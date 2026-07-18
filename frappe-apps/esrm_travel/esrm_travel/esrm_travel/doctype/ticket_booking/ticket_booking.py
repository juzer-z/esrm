import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, nowdate
import re


class TicketBooking(Document):
    def autoname(self):
        settings_series = None
        if frappe.db.exists("DocType", "ESRM Travel Settings"):
            settings_series = frappe.db.get_single_value("ESRM Travel Settings", "ticket_booking_series")

        series = settings_series or self.naming_series or "TB-.YYYY.-"
        self.naming_series = series
        self.name = make_autoname(series)

    def before_validate(self):
        if not self.booking_owner or (self.is_new() and self.booking_owner == "Administrator"):
            self.booking_owner = frappe.session.user
        if not self.approval_status:
            self.approval_status = "Draft"
        if not self.invoice_number:
            self.invoice_number = self.get_next_invoice_number()

    def validate(self):
        self.validate_amounts()
        self.calculate_profitability()
        self.validate_invoice_number()
        self.set_route_summary()
        self.sync_invoice_details()
        self.set_status()

    def before_update_after_submit(self):
        self.validate_amounts()
        self.calculate_profitability()

    def validate_amounts(self):
        amount_fields = [
            "gross_amount",
            "iata_amount",
            "supplier_cost",
            "invoice_amount",
            "paid_amount",
            "outstanding_amount",
        ]
        for fieldname in amount_fields:
            value = flt(self.get(fieldname))
            if value < 0:
                frappe.throw(_("{0} cannot be negative.").format(self.meta.get_label(fieldname)))

        if flt(self.paid_amount) > flt(self.invoice_amount) and flt(self.invoice_amount) > 0:
            frappe.throw(_("Paid Amount cannot be greater than Invoice Amount."))

    def calculate_profitability(self):
        gross_amount = flt(self.gross_amount)
        iata_amount = flt(self.iata_amount)
        supplier_cost = flt(self.supplier_cost)
        invoice_amount = flt(self.invoice_amount)

        if self.payment_mode == "IATA":
            self.commission = gross_amount - iata_amount
            self.profit = invoice_amount - iata_amount
        else:
            self.commission = 0
            self.profit = invoice_amount - supplier_cost

        self.discount = gross_amount - invoice_amount

    def validate_invoice_number(self):
        if not self.invoice_number:
            return

        duplicate = frappe.db.exists(
            "Ticket Booking",
            {
                "invoice_number": self.invoice_number,
                "name": ["!=", self.name],
            },
        )
        if duplicate:
            frappe.throw(_("Invoice Number {0} is already used in Ticket Booking {1}.").format(self.invoice_number, duplicate))

    def get_next_invoice_number(self):
        prefix = self.get_invoice_prefix()
        existing_numbers = frappe.db.sql(
            """
            select invoice_number
            from `tabTicket Booking`
            where invoice_number like %(invoice_prefix)s
              and name != %(name)s
            """,
            {"invoice_prefix": f"{prefix}-%", "name": self.name or ""},
            as_dict=True,
        )

        next_number = 1
        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
        for row in existing_numbers:
            match = pattern.match(row.invoice_number or "")
            if match:
                next_number = max(next_number, int(match.group(1)) + 1)

        return f"{prefix}-{next_number}"

    def get_invoice_prefix(self):
        reference = (self.reference or "").strip()
        if reference:
            return clean_invoice_prefix(reference)

        if self.customer:
            customer_code = frappe.db.get_value("Customer", self.customer, "esrm_customer_code")
            short_name = frappe.db.get_value("Customer", self.customer, "esrm_short_name")
            customer_name = customer_code or short_name or self.customer
            if customer_name:
                return clean_invoice_prefix(customer_name)

        return "OTHERS"

    def set_route_summary(self):
        if self.sectors:
            hops = []
            for row in self.sectors:
                if row.origin and row.destination:
                    hops.append(f"{row.origin}-{row.destination}")
            self.route_summary = " / ".join(hops)

    def sync_invoice_details(self):
        if not self.sales_invoice:
            self.invoice_status = "Not Invoiced"
            self.outstanding_amount = flt(self.invoice_amount) - flt(self.paid_amount)
            return

        invoice = frappe.db.get_value(
            "Sales Invoice",
            self.sales_invoice,
            ["name", "status", "grand_total", "outstanding_amount"],
            as_dict=True,
        )
        if not invoice:
            self.sales_invoice = None
            self.invoice_status = "Not Invoiced"
            self.outstanding_amount = flt(self.invoice_amount) - flt(self.paid_amount)
            return

        self.invoice_status = invoice.status or "Draft"
        self.invoice_amount = flt(invoice.grand_total)
        self.outstanding_amount = flt(invoice.outstanding_amount)
        self.paid_amount = max(flt(self.invoice_amount) - flt(self.outstanding_amount), 0)

    def set_status(self):
        if self.docstatus == 2:
            self.status = "Cancelled"
            return

        if self.sales_invoice:
            if flt(self.outstanding_amount) <= 0 and flt(self.invoice_amount) > 0:
                self.status = "Paid"
            elif flt(self.paid_amount) > 0:
                self.status = "Partially Paid"
            else:
                self.status = "Invoiced"
            return

        flight_date = getdate(self.flight_date) if self.flight_date else None
        today = getdate(nowdate())

        if flight_date and flight_date < today:
            self.status = "Travelled"
        else:
            if self.status in {"Invoiced", "Partially Paid", "Paid", "Cancelled"} or not self.status:
                self.status = "Draft"


@frappe.whitelist()
def make_sales_invoice(source_name):
    booking = frappe.get_doc("Ticket Booking", source_name)

    if booking.sales_invoice:
        return booking.sales_invoice
    if booking.approval_status != "Approved":
        frappe.throw(_("Only approved ticket bookings can be invoiced."))

    settings = frappe.get_single("ESRM Travel Settings")

    if not settings.default_company:
        frappe.throw(_("Set Default Company in ESRM Travel Settings first."))
    if not settings.default_service_item:
        frappe.throw(_("Set Default Service Item in ESRM Travel Settings first."))
    if not booking.customer:
        frappe.throw(_("Customer is required before creating a Sales Invoice."))

    rate = flt(booking.invoice_amount) or flt(booking.gross_amount)
    if rate <= 0:
        frappe.throw(_("Invoice Amount or Gross Amount must be greater than zero."))

    item_row = {
        "item_code": settings.default_service_item,
        "qty": 1,
        "rate": rate,
        "description": build_invoice_description(booking),
    }

    if settings.default_cost_center:
        item_row["cost_center"] = settings.default_cost_center
    if settings.default_income_account:
        item_row["income_account"] = settings.default_income_account

    sales_invoice = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "customer": booking.customer,
            "company": settings.default_company,
            "posting_date": nowdate(),
            "due_date": booking.flight_date or booking.issue_date or nowdate(),
            "esrm_invoice_number": booking.invoice_number,
            "items": [item_row],
            "esrm_ticket_booking": booking.name,
            "remarks": build_invoice_description(booking),
        }
    )
    sales_invoice.insert(ignore_permissions=True)

    booking.db_set("sales_invoice", sales_invoice.name)
    booking.db_set("invoice_status", sales_invoice.status or "Draft")
    booking.db_set("status", "Invoiced")

    return sales_invoice.name


def build_invoice_description(booking):
    parts = [
        f"Invoice No: {booking.invoice_number}" if booking.invoice_number else "",
        f"Passenger: {booking.passenger_name}" if booking.passenger_name else "",
        f"PNR: {booking.pnr}" if booking.pnr else "",
        f"Ticket No: {booking.ticket_number}" if booking.ticket_number else "",
        f"Route: {booking.route_summary}" if booking.route_summary else "",
        f"Airline: {booking.airline}" if booking.airline else "",
        f"Flight Date: {booking.flight_date}" if booking.flight_date else "",
    ]
    return "\n".join(part for part in parts if part)


def clean_invoice_prefix(value):
    prefix = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().upper()).strip("-")
    return prefix or "OTHERS"
