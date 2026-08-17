import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import add_days, add_months, flt, getdate, nowdate


PACKAGE_FIELDS = (
    "country",
    "visa_category",
    "visa_type",
    "processing_type",
    "number_of_entries",
    "currency",
    "government_fee",
    "service_charge",
    "other_charges",
    "default_supplier",
    "default_supplier_cost",
    "expected_processing_days",
    "description",
    "required_documents",
)

INVOICE_BOUND_FIELDS = {
    "customer",
    "reference",
    "invoice_number",
    "application_date",
    "purpose",
    "applicant_name",
    "passport_number",
    "destination_country",
    "visa_category",
    "visa_type",
    "processing_type",
    "number_of_entries",
    "currency",
    "government_fee",
    "service_charge",
    "other_charges",
    "discount",
    "invoice_amount",
    "customer_remarks",
}


class VisaService(Document):
    def autoname(self):
        settings_series = None
        if frappe.db.exists("DocType", "ESRM Travel Settings"):
            settings_series = frappe.db.get_single_value(
                "ESRM Travel Settings", "visa_service_series"
            )
        series = settings_series or self.naming_series or "VS-.YYYY.-"
        self.naming_series = series
        self.name = make_autoname(series)

    def before_validate(self):
        if self.is_new() and not self.service_owner:
            self.service_owner = frappe.session.user
        elif not self.is_new() and frappe.session.user != "Administrator":
            self.service_owner = (
                frappe.db.get_value("Visa Service", self.name, "service_owner")
                or frappe.session.user
            )

        if not self.approval_status:
            self.approval_status = "Draft"
        if not self.application_status:
            self.application_status = "Draft"
        if not self.invoice_number:
            self.invoice_number = self.get_next_invoice_number()

        if self.service_package and (
            self.is_new() or self.has_value_changed("service_package")
        ):
            self.apply_service_package()

    def validate(self):
        self.validate_package()
        self.validate_dates()
        self.validate_amounts()
        self.calculate_amounts()
        self.validate_duplicate_application()
        self.update_document_audit()
        self.validate_stage_requirements()
        self.sync_invoice_details()
        self.set_status()

    def before_submit(self):
        if self.approval_status == "Approved" and self.application_status in {
            "Draft", "Documents Pending", "Ready for Approval"
        }:
            self.application_status = "Approved"

    def before_update_after_submit(self):
        self.validate_submitted_changes()
        self.validate_dates()
        self.validate_amounts()
        self.calculate_amounts()
        self.update_document_audit()
        self.validate_stage_requirements()

    def apply_service_package(self):
        package = frappe.get_doc("Visa Service Package", self.service_package)
        if not package.active:
            frappe.throw(_("Visa Service Package {0} is inactive.").format(package.name))
        today = getdate(nowdate())
        if package.effective_from and getdate(package.effective_from) > today:
            frappe.throw(_("Visa Service Package {0} is not effective yet.").format(package.name))
        if package.effective_until and getdate(package.effective_until) < today:
            frappe.throw(_("Visa Service Package {0} has expired.").format(package.name))

        self.destination_country = package.country
        self.visa_category = package.visa_category
        self.visa_type = package.visa_type
        self.processing_type = package.processing_type
        self.number_of_entries = package.number_of_entries
        self.currency = package.currency
        self.government_fee = package.government_fee
        self.service_charge = package.service_charge
        self.other_charges = package.other_charges
        self.supplier = package.default_supplier
        self.supplier_cost = package.default_supplier_cost
        self.expected_processing_days = package.expected_processing_days
        self.service_description = package.description or package.package_name

        self.set("documents", [])
        for document_type in parse_required_documents(package.required_documents):
            self.append(
                "documents",
                {"document_type": document_type, "required": 1},
            )

    def validate_package(self):
        if not self.service_package:
            return
        package = frappe.db.get_value(
            "Visa Service Package",
            self.service_package,
            ["active", "country"],
            as_dict=True,
        )
        if not package or not package.active:
            frappe.throw(_("Select an active Visa Service Package."))
        if package.country != self.destination_country:
            frappe.throw(_("Destination Country must match the selected package."))

    def validate_dates(self):
        if self.intended_travel_date and self.intended_return_date:
            if getdate(self.intended_return_date) < getdate(self.intended_travel_date):
                frappe.throw(_("Intended Return Date cannot be before Intended Travel Date."))
        if self.passport_expiry_date and self.intended_travel_date:
            if getdate(self.passport_expiry_date) <= getdate(self.intended_travel_date):
                frappe.throw(_("Passport must remain valid after the intended travel date."))
            if getdate(self.passport_expiry_date) < add_months(
                getdate(self.intended_travel_date), 6
            ):
                frappe.msgprint(
                    _("Passport validity is less than six months from the intended travel date."),
                    indicator="orange",
                    alert=True,
                )
        if self.visa_valid_from and self.visa_valid_until:
            if getdate(self.visa_valid_until) < getdate(self.visa_valid_from):
                frappe.throw(_("Visa Valid Until cannot be before Visa Valid From."))
        if self.application_date and self.expected_processing_days:
            self.expected_completion_date = add_days(
                getdate(self.application_date), int(self.expected_processing_days)
            )

    def validate_amounts(self):
        for fieldname in (
            "government_fee",
            "service_charge",
            "other_charges",
            "discount",
            "supplier_cost",
        ):
            if flt(self.get(fieldname)) < 0:
                frappe.throw(_("{0} cannot be negative.").format(self.meta.get_label(fieldname)))
        gross = flt(self.government_fee) + flt(self.service_charge) + flt(self.other_charges)
        if flt(self.discount) > gross:
            frappe.throw(_("Discount cannot exceed the total charges."))

    def calculate_amounts(self):
        self.invoice_amount = (
            flt(self.government_fee)
            + flt(self.service_charge)
            + flt(self.other_charges)
            - flt(self.discount)
        )
        self.total_cost = flt(self.supplier_cost)
        self.profit = flt(self.invoice_amount) - flt(self.total_cost)
        if not self.sales_invoice:
            self.outstanding_amount = self.invoice_amount
            self.paid_amount = 0

    def validate_duplicate_application(self):
        if not self.passport_number or not self.destination_country or not self.visa_category:
            return
        duplicate = frappe.db.exists(
            "Visa Service",
            {
                "name": ["!=", self.name],
                "passport_number": self.passport_number.strip(),
                "destination_country": self.destination_country,
                "visa_category": self.visa_category,
                "application_status": ["not in", ["Completed", "Cancelled", "Refunded", "Visa Rejected"]],
            },
        )
        if duplicate:
            frappe.throw(
                _("Active Visa Service {0} already exists for this passport, country and category.").format(duplicate)
            )

    def update_document_audit(self):
        for row in self.documents or []:
            if row.received and not row.received_date:
                row.received_date = nowdate()
            if row.verified:
                if not row.received:
                    frappe.throw(_("Mark {0} as received before verifying it.").format(row.document_type))
                if not row.verified_by:
                    row.verified_by = frappe.session.user
            elif row.verified_by:
                row.verified_by = None

    def validate_stage_requirements(self):
        if self.approval_status in {"Pending Approval", "Approved"}:
            if flt(self.invoice_amount) <= 0:
                frappe.throw(_("Invoice Amount must be greater than zero before approval."))

        if self.application_status in {
            "Submitted", "Under Processing", "Additional Documents Required",
            "Decision Received", "Visa Approved", "Visa Rejected", "Completed",
        }:
            missing = [
                row.document_type
                for row in self.documents or []
                if row.required and (not row.received or not row.verified)
            ]
            if missing:
                frappe.throw(
                    _("Receive and verify all required documents before submission: {0}").format(", ".join(missing))
                )
            if not self.submission_date or not self.submitted_to:
                frappe.throw(_("Submission Date and Submitted To are required at the Submitted stage."))

        if self.application_status in {"Visa Approved", "Visa Rejected", "Completed"}:
            if not self.decision or not self.decision_date:
                frappe.throw(_("Decision and Decision Date are required after a decision is received."))
        if self.decision == "Approved":
            if not self.visa_copy or not self.visa_valid_from or not self.visa_valid_until:
                frappe.throw(_("Visa Copy and visa validity dates are required for an approved visa."))
        if self.decision == "Rejected" and not self.rejection_reason:
            frappe.throw(_("Rejection Reason is required for a rejected visa."))
        if self.application_status == "Completed" and not self.delivered_date:
            frappe.throw(_("Collected / Delivered Date is required to complete the service."))

    def validate_submitted_changes(self):
        previous = self.get_doc_before_save()
        if not previous:
            return
        changed = {
            field.fieldname
            for field in self.meta.fields
            if field.fieldtype not in {"Section Break", "Column Break", "Tab Break", "HTML", "Button"}
            and self.has_value_changed(field.fieldname)
        }
        invoice_changes = changed & INVOICE_BOUND_FIELDS
        if self.sales_invoice and invoice_changes:
            invoice_docstatus = frappe.db.get_value("Sales Invoice", self.sales_invoice, "docstatus")
            if invoice_docstatus == 1:
                frappe.throw(
                    _("Fields used by submitted Sales Invoice {0} cannot be changed: {1}.").format(
                        self.sales_invoice,
                        ", ".join(self.meta.get_label(fieldname) or fieldname for fieldname in sorted(invoice_changes)),
                    )
                )

    def sync_invoice_details(self):
        if not self.sales_invoice:
            self.invoice_status = "Not Invoiced"
            return
        invoice = frappe.db.get_value(
            "Sales Invoice",
            self.sales_invoice,
            ["status", "grand_total", "outstanding_amount", "docstatus"],
            as_dict=True,
        )
        if not invoice:
            self.sales_invoice = None
            self.invoice_status = "Not Invoiced"
            return
        row_amount = flt(
            frappe.db.get_value(
                "ESRM Invoice Visa Service",
                {"parent": self.sales_invoice, "parenttype": "Sales Invoice", "visa_service": self.name},
                "amount",
            )
        ) or flt(self.invoice_amount)
        ratio = 0
        if flt(invoice.grand_total) > 0:
            ratio = max(flt(invoice.grand_total) - flt(invoice.outstanding_amount), 0) / flt(invoice.grand_total)
        self.invoice_status = invoice.status or "Draft"
        self.paid_amount = row_amount * ratio
        self.outstanding_amount = max(row_amount - self.paid_amount, 0)

    def set_status(self):
        if self.docstatus == 2 or self.application_status == "Cancelled":
            self.status = "Cancelled"
        elif self.application_status == "Refunded":
            self.status = "Refunded"
        elif self.application_status == "Completed":
            self.status = "Completed"
        elif self.sales_invoice:
            if flt(self.outstanding_amount) <= 0 and flt(self.invoice_amount) > 0:
                self.status = "Paid"
            elif flt(self.paid_amount) > 0:
                self.status = "Partially Paid"
            else:
                self.status = "Invoiced"
        else:
            self.status = "Draft"

    def get_next_invoice_number(self):
        prefix = self.get_invoice_prefix()
        rows = []
        for doctype in ("Ticket Booking", "Visa Service"):
            if frappe.db.exists("DocType", doctype):
                rows.extend(
                    frappe.get_all(
                        doctype,
                        filters={"invoice_number": ["like", f"{prefix}-%"], "name": ["!=", self.name or ""]},
                        pluck="invoice_number",
                    )
                )
        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
        number = 1
        for value in rows:
            match = pattern.match(value or "")
            if match:
                number = max(number, int(match.group(1)) + 1)
        return f"{prefix}-{number}"

    def get_invoice_prefix(self):
        value = (self.reference or "").strip()
        if not value and self.customer:
            value = (
                frappe.db.get_value("Customer", self.customer, "esrm_customer_code")
                or frappe.db.get_value("Customer", self.customer, "esrm_short_name")
                or self.customer
            )
        return clean_invoice_prefix(value or "OTHERS")


@frappe.whitelist()
def get_package_defaults(package_name):
    package = frappe.get_doc("Visa Service Package", package_name)
    return {
        "destination_country": package.country,
        "visa_category": package.visa_category,
        "visa_type": package.visa_type,
        "processing_type": package.processing_type,
        "number_of_entries": package.number_of_entries,
        "currency": package.currency,
        "government_fee": package.government_fee,
        "service_charge": package.service_charge,
        "other_charges": package.other_charges,
        "supplier": package.default_supplier,
        "supplier_cost": package.default_supplier_cost,
        "expected_processing_days": package.expected_processing_days,
        "service_description": package.description or package.package_name,
        "documents": parse_required_documents(package.required_documents),
    }


@frappe.whitelist()
def make_sales_invoice(source_name):
    return make_sales_invoice_from_services([source_name])


@frappe.whitelist()
def make_group_sales_invoice(services):
    if isinstance(services, str):
        services = frappe.parse_json(services)
    return make_sales_invoice_from_services(services)


def make_sales_invoice_from_services(service_names):
    if not service_names:
        frappe.throw(_("Select at least one Visa Service."))
    services = [frappe.get_doc("Visa Service", name) for name in service_names]
    customer = services[0].customer
    for service in services:
        if service.docstatus != 1 or service.approval_status != "Approved":
            frappe.throw(_("Only approved, submitted Visa Services can be invoiced."))
        if service.sales_invoice:
            frappe.throw(_("Visa Service {0} is already invoiced.").format(service.name))
        if service.customer != customer:
            frappe.throw(_("All selected Visa Services must have the same Customer."))
        if flt(service.invoice_amount) <= 0:
            frappe.throw(_("Visa Service {0} must have a positive Invoice Amount.").format(service.name))

    settings = frappe.get_single("ESRM Travel Settings")
    if not settings.default_company or not settings.default_service_item:
        frappe.throw(_("Set Default Company and Default Service Item in ESRM Settings first."))
    company_currency = frappe.db.get_value("Company", settings.default_company, "default_currency") or "BDT"
    for service in services:
        if service.currency != company_currency:
            frappe.throw(
                _("Visa Service {0} uses {1}. The first release supports company currency {2} only.").format(
                    service.name, service.currency, company_currency
                )
            )
    income_account = getattr(settings, "visa_income_account", None) or settings.default_income_account
    if not income_account:
        frappe.throw(_("Set Visa Service Income Account in ESRM Settings first."))
    price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"

    items = []
    detail_rows = []
    for service in services:
        item = {
            "item_code": settings.default_service_item,
            "qty": 1,
            "rate": service.invoice_amount,
            "description": build_invoice_description(service),
            "income_account": income_account,
        }
        if settings.default_cost_center:
            item["cost_center"] = settings.default_cost_center
        items.append(item)
        detail_rows.append(build_invoice_row(service))

    invoice = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "customer": customer,
            "company": settings.default_company,
            "currency": company_currency,
            "conversion_rate": 1,
            "selling_price_list": price_list,
            "price_list_currency": company_currency,
            "plc_conversion_rate": 1,
            "posting_date": nowdate(),
            "due_date": nowdate(),
            "esrm_invoice_number": services[0].invoice_number,
            "esrm_visa_service": services[0].name,
            "esrm_visa_services": detail_rows,
            "items": items,
            "remarks": "\n\n".join(build_invoice_description(service) for service in services),
        }
    )
    invoice.insert(ignore_permissions=True)
    for service in services:
        frappe.db.set_value(
            "Visa Service",
            service.name,
            {"sales_invoice": invoice.name, "invoice_status": invoice.status or "Draft", "status": "Invoiced"},
            update_modified=True,
        )
    return invoice.name


def build_invoice_row(service):
    return {
        "visa_service": service.name,
        "application_date": service.application_date,
        "applicant_name": service.applicant_name,
        "passport_number": mask_passport(service.passport_number),
        "country": service.destination_country,
        "service_description": get_service_summary(service),
        "amount": service.invoice_amount,
        "remarks": service.customer_remarks,
    }


def build_invoice_description(service):
    parts = [
        f"Invoice No: {service.invoice_number}" if service.invoice_number else "",
        f"Applicant: {service.applicant_name}",
        f"Passport: {mask_passport(service.passport_number)}",
        f"Service: {get_service_summary(service)}",
        f"Travel Date: {service.intended_travel_date}" if service.intended_travel_date else "",
    ]
    return "\n".join(part for part in parts if part)


def get_service_summary(service):
    return " - ".join(
        value
        for value in (
            service.destination_country,
            service.visa_category,
            service.visa_type,
            service.processing_type,
        )
        if value
    )


def parse_required_documents(value):
    return list(
        dict.fromkeys(
            line.strip()
            for line in (value or "").replace(",", "\n").splitlines()
            if line.strip()
        )
    )


def mask_passport(value):
    value = (value or "").strip()
    if len(value) <= 4:
        return value
    return f"{value[0]}{'*' * (len(value) - 3)}{value[-2:]}"


def clean_invoice_prefix(value):
    return re.sub(r"[^A-Za-z0-9]+", "-", value.strip().upper()).strip("-") or "OTHERS"
