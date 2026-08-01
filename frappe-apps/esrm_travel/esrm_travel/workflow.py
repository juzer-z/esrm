import frappe
from frappe import _
from frappe.utils import flt, getdate


PAYMENT_MODE_MAP = {
    "Cash": {"mode_of_payment": "Cash", "company_account_field": "default_cash_account"},
    "Bank Transfer": {
        "mode_of_payment": "Wire Transfer",
        "company_account_field": "default_bank_account",
    },
    "Card": {"mode_of_payment": "Credit Card", "company_account_field": "default_bank_account"},
}


@frappe.whitelist()
def bulk_submit_sales_invoices(invoice_names):
    if frappe.session.user != "Administrator":
        frappe.throw(
            _("Only Administrator can bulk-submit Sales Invoices."),
            frappe.PermissionError,
        )

    if isinstance(invoice_names, str):
        invoice_names = frappe.parse_json(invoice_names)

    invoice_names = list(dict.fromkeys(invoice_names or []))
    if not invoice_names:
        frappe.throw(_("Select at least one draft Sales Invoice."))
    if len(invoice_names) > 100:
        frappe.throw(_("Submit no more than 100 Sales Invoices at a time."))

    submitted = []
    failed = []
    for index, invoice_name in enumerate(invoice_names):
        savepoint = f"bulk_invoice_submit_{index}"
        frappe.db.savepoint(savepoint)
        try:
            invoice = frappe.get_doc("Sales Invoice", invoice_name)
            if invoice.docstatus != 0:
                frappe.throw(_("Invoice is not a draft."))
            prepare_invoice_dates_for_submission(invoice)
            invoice.submit()
            submitted.append(invoice_name)
        except Exception as exc:
            frappe.db.rollback(save_point=savepoint)
            failed.append({"name": invoice_name, "error": str(exc)})
            frappe.clear_messages()

    return {"submitted": submitted, "failed": failed}


def prepare_invoice_dates_for_submission(invoice):
    """Keep the draft's displayed posting date when submitting it in bulk."""
    if invoice.meta.has_field("set_posting_time"):
        invoice.set_posting_time = 1

    posting_date = getdate(invoice.posting_date)
    if not invoice.due_date or getdate(invoice.due_date) < posting_date:
        invoice.due_date = posting_date

    for payment in invoice.get("payment_schedule") or []:
        if not payment.due_date or getdate(payment.due_date) < posting_date:
            payment.due_date = posting_date


def before_validate_payment_entry(doc, method=None):
    booking_names = get_related_ticket_bookings_from_payment_entry(doc)

    if len(booking_names) == 1:
        booking_name = next(iter(booking_names))
        if not doc.esrm_ticket_booking:
            doc.esrm_ticket_booking = booking_name

        booking = frappe.get_doc("Ticket Booking", booking_name)
        payment_defaults = PAYMENT_MODE_MAP.get(booking.payment_mode)
        if not payment_defaults or doc.payment_type != "Receive":
            return

        if not doc.mode_of_payment:
            doc.mode_of_payment = payment_defaults["mode_of_payment"]

        target_account = get_company_payment_account(
            doc.company, payment_defaults["mode_of_payment"], payment_defaults["company_account_field"]
        )
        if target_account and doc.is_new():
            doc.paid_to = target_account


def on_submit_sales_invoice(doc, method=None):
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        sync_ticket_booking(booking_name, sales_invoice_name=doc.name)


def on_update_after_submit_sales_invoice(doc, method=None):
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        sync_ticket_booking(booking_name, sales_invoice_name=doc.name)


def on_cancel_sales_invoice(doc, method=None):
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        sync_ticket_booking(booking_name, sales_invoice_name=doc.name, clear_sales_invoice=True)


def after_delete_sales_invoice(doc, method=None):
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        sync_ticket_booking(booking_name, sales_invoice_name=doc.name, clear_sales_invoice=True)


def on_submit_payment_entry(doc, method=None):
    for booking_name in get_related_ticket_bookings_from_payment_entry(doc):
        sync_ticket_booking(booking_name)


def on_update_after_submit_payment_entry(doc, method=None):
    for booking_name in get_related_ticket_bookings_from_payment_entry(doc):
        sync_ticket_booking(booking_name)


def on_cancel_payment_entry(doc, method=None):
    for booking_name in get_related_ticket_bookings_from_payment_entry(doc):
        sync_ticket_booking(booking_name)


def get_related_ticket_bookings_from_payment_entry(doc):
    booking_names = set()

    if getattr(doc, "esrm_ticket_booking", None):
        booking_names.add(doc.esrm_ticket_booking)

    for row in doc.get("references", []):
        if row.reference_doctype != "Sales Invoice" or not row.reference_name:
            continue
        invoice = frappe.get_doc("Sales Invoice", row.reference_name)
        booking_names.update(get_related_ticket_bookings_from_sales_invoice(invoice))

    return booking_names


def get_related_ticket_bookings_from_sales_invoice(doc):
    booking_names = set()

    if getattr(doc, "esrm_ticket_booking", None):
        booking_names.add(doc.esrm_ticket_booking)

    for row in doc.get("esrm_ticket_bookings", []):
        if row.ticket_booking:
            booking_names.add(row.ticket_booking)

    return booking_names


def get_company_payment_account(company, mode_of_payment, company_account_field):
    account = frappe.db.get_value(
        "Mode of Payment Account",
        {"parent": mode_of_payment, "company": company},
        "default_account",
    )
    if account:
        return account

    return frappe.db.get_value("Company", company, company_account_field)


def sync_ticket_booking(booking_name, sales_invoice_name=None, clear_sales_invoice=False):
    if not booking_name or not frappe.db.exists("Ticket Booking", booking_name):
        return

    booking = frappe.get_doc("Ticket Booking", booking_name)

    if clear_sales_invoice and booking.sales_invoice == sales_invoice_name:
        booking.sales_invoice = None
        booking.invoice_status = "Not Invoiced"
        booking.paid_amount = 0
        booking.outstanding_amount = flt(booking.invoice_amount) or flt(booking.gross_amount)
    elif sales_invoice_name and not booking.sales_invoice:
        booking.sales_invoice = sales_invoice_name

    if not clear_sales_invoice:
        booking.sync_invoice_details()

    booking.set_status()
    frappe.db.set_value(
        "Ticket Booking",
        booking.name,
        {
            "sales_invoice": booking.sales_invoice,
            "invoice_status": booking.invoice_status,
            "invoice_amount": booking.invoice_amount,
            "paid_amount": booking.paid_amount,
            "outstanding_amount": booking.outstanding_amount,
            "status": booking.status,
        },
        update_modified=True,
    )
