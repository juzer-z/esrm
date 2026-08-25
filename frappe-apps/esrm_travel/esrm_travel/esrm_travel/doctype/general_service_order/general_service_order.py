import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, now, nowdate


INVOICE_BOUND_FIELDS = {
    "customer", "reference", "invoice_number", "entry_date", "service_family",
    "service_offering", "calculation_profile", "subject", "description",
    "client_reference", "purchase_order", "attention_to", "service_period_from",
    "service_period_to", "currency", "print_profile", "signatory_name",
    "signatory_designation", "charges", "applicants", "annexure_details",
    "customer_remarks",
}


class GeneralServiceOrder(Document):
    def autoname(self):
        series = frappe.db.get_single_value("ESRM Travel Settings", "general_service_order_series") if frappe.db.exists("DocType", "ESRM Travel Settings") else None
        self.naming_series = series or self.naming_series or "GSO-.YYYY.-"
        self.name = make_autoname(self.naming_series)

    def before_validate(self):
        if frappe.session.user != "Administrator":
            if self.is_new():
                self.service_owner = frappe.session.user
            else:
                self.service_owner = frappe.db.get_value(self.doctype, self.name, "service_owner") or frappe.session.user
        elif self.is_new() and not self.service_owner:
            self.service_owner = frappe.session.user
        self.approval_status = self.approval_status or "Draft"
        if not self.invoice_number:
            self.invoice_number = self.get_next_invoice_number()

    def validate(self):
        self.apply_offering_requirements()
        self.calculate_totals()
        if self.approval_status in {"Pending Approval", "Approved"} and flt(self.invoice_amount) <= 0:
            frappe.throw(_("Invoice Amount must be greater than zero."))
        self.sync_invoice_details()
        self.set_status()

    def before_update_after_submit(self):
        self.validate_submitted_changes()
        self.apply_offering_requirements()
        self.calculate_totals()

    def on_submit(self):
        if self.approval_status != "Approved":
            frappe.throw(_("Only an approved General Service Order can be submitted."))
        self.create_sales_invoice_on_approval()

    def on_update_after_submit(self):
        if getattr(self, "_replace_linked_invoice", None):
            self.replace_linked_sales_invoice()
        elif getattr(self, "_invoice_amendment_fields", None) and not self.sales_invoice:
            self.create_corrected_invoice_after_unlinked_amendment()
        if getattr(self, "_invoice_amendment_fields", None):
            self.add_comment("Edit", _("Administrator amended invoice fields: {0}. Reason: {1}").format(", ".join(self._invoice_amendment_fields), self.amendment_reason))

    def apply_offering_requirements(self):
        if not self.service_offering:
            return
        offering = frappe.get_doc("Service Offering", self.service_offering)
        if not offering.active:
            frappe.throw(_("Service Offering {0} is inactive.").format(offering.name))
        if offering.po_required and not self.purchase_order:
            frappe.throw(_("Purchase Order is required for this service offering."))
        if offering.billing_period_required and (not self.service_period_from or not self.service_period_to):
            frappe.throw(_("Service Period From and To are required for this service offering."))
        if offering.applicant_details_required and not self.applicants:
            frappe.throw(_("Add at least one applicant for this service offering."))

    def calculate_totals(self):
        invoice = withholding = revenue = cost = 0
        for row in self.charges:
            row.amount = flt(row.basis_amount) * flt(row.percentage) / 100 if flt(row.percentage) else flt(row.quantity or 1) * flt(row.rate)
            if row.charge_type == "Discount" and row.amount > 0:
                row.amount *= -1
            if row.included_in_invoice:
                invoice += row.amount
            if row.is_withholding:
                withholding += abs(row.amount)
            if row.is_revenue:
                revenue += row.amount
            cost += flt(row.actual_cost)
        self.invoice_amount = invoice
        self.expected_withholding = withholding
        self.net_expected_receipt = invoice - withholding
        self.revenue_amount = revenue
        self.total_cost = cost
        self.profit = revenue - cost

    def create_sales_invoice_on_approval(self):
        if self.sales_invoice:
            return
        try:
            invoice_name = make_and_submit_sales_invoice([self.name])
        except Exception as exc:
            frappe.log_error(title=f"Automatic general service invoice failed for {self.name}", message=frappe.get_traceback())
            frappe.throw(_("General Service Order {0} could not be approved because its submitted Sales Invoice could not be created. Reason: {1}").format(self.name, str(exc)))
        self.sales_invoice = invoice_name
        self.invoice_status = frappe.db.get_value("Sales Invoice", invoice_name, "status") or "Unpaid"
        self.status = "Invoiced"

    def validate_submitted_changes(self):
        previous = self.get_doc_before_save()
        if not previous:
            return
        changed = {field.fieldname for field in self.meta.fields if field.fieldtype not in {"Section Break", "Column Break", "Tab Break", "HTML", "Button"} and self.has_value_changed(field.fieldname)}
        invoice_changes = changed & INVOICE_BOUND_FIELDS
        if not invoice_changes:
            return
        if frappe.session.user != "Administrator":
            frappe.throw(_("Only Administrator can amend fields used by a General Service invoice."), frappe.PermissionError)
        reason = (self.amendment_reason or "").strip()
        if not reason or not self.has_value_changed("amendment_reason"):
            frappe.throw(_("Enter a new Amendment Reason before saving invoice changes."))
        self.last_amended_by = frappe.session.user
        self.last_amended_at = now()
        self.amendment_count = (previous.amendment_count or 0) + 1
        self._invoice_amendment_fields = sorted(invoice_changes)
        if self.sales_invoice:
            self._replace_linked_invoice = self.sales_invoice

    def replace_linked_sales_invoice(self):
        from esrm_travel.workflow import cancel_sales_invoice, sync_general_service_order
        old_name = self._replace_linked_invoice
        old = frappe.get_doc("Sales Invoice", old_name)
        old_status = old.docstatus
        if old_status == 1:
            cancel_sales_invoice(old_name)
        elif old_status == 0:
            old.flags.ignore_permissions = True
            old.delete()
        else:
            sync_general_service_order(self.name, old_name, clear_sales_invoice=True)
        self.sales_invoice = make_and_submit_sales_invoice([self.name], amended_from=old_name if old_status in {1, 2} else None)

    def create_corrected_invoice_after_unlinked_amendment(self):
        previous = frappe.db.sql("""select invoice.name from `tabSales Invoice` invoice inner join `tabESRM Invoice General Service` detail on detail.parent=invoice.name and detail.parenttype='Sales Invoice' where detail.general_service_order=%s and invoice.docstatus=2 and ifnull(invoice.is_return,0)=0 order by invoice.modified desc limit 1""", self.name)
        self.sales_invoice = make_and_submit_sales_invoice([self.name], amended_from=previous[0][0] if previous else None)

    def sync_invoice_details(self):
        if not self.sales_invoice:
            self.invoice_status = "Not Invoiced"
            return
        invoice = frappe.db.get_value("Sales Invoice", self.sales_invoice, ["status", "grand_total", "outstanding_amount", "docstatus"], as_dict=True)
        if not invoice:
            self.sales_invoice = None
            self.invoice_status = "Not Invoiced"
            return
        self.invoice_status = invoice.status or "Draft"
        paid = max(flt(invoice.grand_total) - flt(invoice.outstanding_amount), 0)
        self.db_set("paid_amount", paid, update_modified=False) if self.meta.has_field("paid_amount") else None

    def set_status(self):
        if self.docstatus == 2:
            self.status = "Cancelled"
        elif self.sales_invoice:
            outstanding = flt(frappe.db.get_value("Sales Invoice", self.sales_invoice, "outstanding_amount"))
            self.status = "Paid" if outstanding <= 0 else "Invoiced"
        else:
            self.status = "Draft"

    def get_next_invoice_number(self):
        prefix = re.sub(r"[^A-Za-z0-9_-]+", "-", (self.reference or self.customer or "GENERAL").strip()).strip("-").upper() or "GENERAL"
        rows = frappe.get_all(self.doctype, filters={"invoice_number":["like", f"{prefix}-%"], "name":["!=", self.name or ""]}, pluck="invoice_number")
        number = 1
        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
        for value in rows:
            match = pattern.match(value or "")
            if match:
                number = max(number, int(match.group(1)) + 1)
        return f"{prefix}-{number}"


@frappe.whitelist()
def get_offering_defaults(offering_name):
    offering = frappe.get_doc("Service Offering", offering_name)
    charges = []
    if flt(offering.default_government_fee):
        charges.append({"charge_type":"Government Fee", "description":"Government / statutory fee", "quantity":1, "rate":offering.default_government_fee, "included_in_invoice":1, "is_revenue":0})
    if flt(offering.default_service_charge):
        charges.append({"charge_type":"Service Charge", "description":offering.default_description or offering.offering_name, "quantity":1, "rate":offering.default_service_charge, "included_in_invoice":1, "is_revenue":1, "actual_cost":offering.default_cost})
    basis = flt(offering.default_government_fee) + flt(offering.default_service_charge)
    if offering.vat_applicable and flt(offering.vat_rate):
        charges.append({"charge_type":"VAT", "description":f"VAT @ {flt(offering.vat_rate)}%", "percentage":offering.vat_rate, "basis_amount":basis, "included_in_invoice":1, "is_revenue":0})
    if offering.ait_applicable and offering.ait_treatment == "Withheld during payment" and flt(offering.ait_rate):
        charges.append({"charge_type":"AIT", "description":f"Expected AIT withholding @ {flt(offering.ait_rate)}%", "percentage":offering.ait_rate, "basis_amount":basis, "included_in_invoice":0, "is_revenue":0, "is_withholding":1})
    if flt(offering.commission_percentage):
        commission_basis = flt(offering.default_service_charge) if offering.commission_basis == "Service Charge" else (flt(offering.default_government_fee) if offering.commission_basis == "Government Fee" else basis)
        charges.append({"charge_type":"Commission", "description":f"Commission @ {flt(offering.commission_percentage)}%", "percentage":offering.commission_percentage, "basis_amount":commission_basis, "included_in_invoice":1, "is_revenue":1})
    return {"service_family":offering.service_family, "calculation_profile":offering.calculation_profile, "description":offering.default_description, "print_profile":"Payroll" if offering.service_family == "Outsourced Payroll" else "Standard", "charges":charges}


def make_and_submit_sales_invoice(order_names, amended_from=None):
    invoice_name = make_sales_invoice_from_orders(order_names, amended_from)
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    invoice.flags.ignore_permissions = True
    invoice.submit()
    return invoice.name


def make_sales_invoice_from_orders(order_names, amended_from=None):
    orders = [frappe.get_doc("General Service Order", name) for name in order_names]
    if not orders:
        frappe.throw(_("Select at least one General Service Order."))
    customer = orders[0].customer
    for order in orders:
        if order.docstatus != 1 or order.approval_status != "Approved" or order.sales_invoice or order.customer != customer:
            frappe.throw(_("Only uninvoiced approved orders for the same Customer can be invoiced."))
    settings = frappe.get_single("ESRM Travel Settings")
    income_account = getattr(settings, "general_service_income_account", None) or settings.default_income_account
    if not settings.default_company or not settings.default_service_item or not income_account:
        frappe.throw(_("Set Default Company, Default Service Item and General Service Income Account in ESRM Settings."))
    currency = frappe.db.get_value("Company", settings.default_company, "default_currency") or "BDT"
    items, details = [], []
    for order in orders:
        if order.currency != currency:
            frappe.throw(_("General Service Order {0} must use company currency {1}.").format(order.name, currency))
        for charge in order.charges:
            if not charge.included_in_invoice or not flt(charge.amount):
                continue
            item = {"item_code":settings.default_service_item, "qty":1, "rate":charge.amount, "description":charge.description, "income_account":income_account}
            if settings.default_cost_center:
                item["cost_center"] = settings.default_cost_center
            items.append(item)
        details.append({"general_service_order":order.name,"service_date":order.entry_date,"service_offering":order.service_offering,"subject":order.subject,"description":order.description,"quantity":1,"amount":order.invoice_amount,"remarks":order.customer_remarks})
    posting_date = orders[0].entry_date or nowdate()
    values = {"doctype":"Sales Invoice","customer":customer,"company":settings.default_company,"currency":currency,"conversion_rate":1,"selling_price_list":frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling","price_list_currency":currency,"plc_conversion_rate":1,"posting_date":posting_date,"due_date":posting_date,"set_posting_time":1,"esrm_invoice_number":orders[0].invoice_number,"esrm_general_service_order":orders[0].name,"esrm_general_services":details,"items":items,"remarks":"\n\n".join(f"{o.subject}\n{o.description or ''}" for o in orders)}
    if amended_from:
        values["amended_from"] = amended_from
    invoice = frappe.get_doc(values)
    invoice.insert(ignore_permissions=True)
    for order in orders:
        frappe.db.set_value("General Service Order", order.name, {"sales_invoice":invoice.name,"invoice_status":invoice.status or "Draft","status":"Invoiced"}, update_modified=True)
    return invoice.name
