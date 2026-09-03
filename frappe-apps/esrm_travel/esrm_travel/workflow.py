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


def set_sales_invoice_search_names(doc, method=None):
    """Keep ESRM operational names searchable on invoices."""
    passenger_names = []
    for row in doc.get("esrm_ticket_bookings") or []:
        passenger_name = (row.passenger_name or "").strip()
        if passenger_name and passenger_name not in passenger_names:
            passenger_names.append(passenger_name)

    doc.esrm_passenger_names = "\n".join(passenger_names)
    applicant_names = []
    for row in doc.get("esrm_visa_services") or []:
        applicant_name = (row.applicant_name or "").strip()
        if applicant_name and applicant_name not in applicant_names:
            applicant_names.append(applicant_name)
    doc.esrm_applicant_names = "\n".join(applicant_names)
    subjects = []
    for row in doc.get("esrm_general_services") or []:
        subject = (row.subject or "").strip()
        if subject and subject not in subjects:
            subjects.append(subject)
    if doc.meta.has_field("esrm_service_subjects"):
        doc.esrm_service_subjects = "\n".join(subjects)


set_sales_invoice_passenger_names = set_sales_invoice_search_names


def backfill_sales_invoice_passenger_names():
    if not frappe.get_meta("Sales Invoice").has_field("esrm_passenger_names"):
        return

    for invoice_name in frappe.get_all("Sales Invoice", pluck="name"):
        passenger_names = []
        rows = frappe.get_all(
            "ESRM Invoice Ticket",
            filters={"parent": invoice_name, "parenttype": "Sales Invoice"},
            fields=["passenger_name"],
            order_by="idx asc",
        )
        for row in rows:
            passenger_name = (row.passenger_name or "").strip()
            if passenger_name and passenger_name not in passenger_names:
                passenger_names.append(passenger_name)

        frappe.db.set_value(
            "Sales Invoice",
            invoice_name,
            "esrm_passenger_names",
            "\n".join(passenger_names),
            update_modified=False,
        )


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


@frappe.whitelist()
def cancel_sales_invoice(invoice_name):
    """Cancel an invoice without cancelling its approved ESRM service records."""
    if frappe.session.user != "Administrator":
        frappe.throw(
            _("Only Administrator can cancel Sales Invoices."),
            frappe.PermissionError,
        )

    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    if invoice.docstatus != 1:
        frappe.throw(_("Only a submitted Sales Invoice can be cancelled."))

    # Ticket Booking and Visa Service are operational source records, not
    # accounting dependants that should be cancelled with their invoice. Clear
    # their back-links first so Frappe can cancel only the Sales Invoice. The
    # request transaction rolls these changes back if accounting cancellation
    # fails for any other reason.
    booking_names = get_related_ticket_bookings_from_sales_invoice(invoice)
    service_names = get_related_visa_services_from_sales_invoice(invoice)
    general_order_names = get_related_general_service_orders_from_sales_invoice(invoice)

    for booking_name in booking_names:
        sync_ticket_booking(
            booking_name,
            sales_invoice_name=invoice.name,
            clear_sales_invoice=True,
        )
    for service_name in service_names:
        sync_visa_service(
            service_name,
            sales_invoice_name=invoice.name,
            clear_sales_invoice=True,
        )
    for order_name in general_order_names:
        sync_general_service_order(order_name, sales_invoice_name=invoice.name, clear_sales_invoice=True)

    # The operational back-links above have already been handled deliberately.
    # Prevent Frappe's generic back-link validator from treating those submitted
    # source records as accounting documents that must also be cancelled.
    invoice.flags.ignore_links = True
    invoice.cancel()

    # Cancellation hooks and framework link processing can refresh cached source
    # documents. Re-apply the intended final state so both the status and the
    # back-link are consistent after cancellation.
    for booking_name in booking_names:
        sync_ticket_booking(
            booking_name,
            sales_invoice_name=invoice.name,
            clear_sales_invoice=True,
        )
    for service_name in service_names:
        sync_visa_service(
            service_name,
            sales_invoice_name=invoice.name,
            clear_sales_invoice=True,
        )
    for order_name in general_order_names:
        sync_general_service_order(order_name, sales_invoice_name=invoice.name, clear_sales_invoice=True)
    return invoice.name


@frappe.whitelist()
def delete_cancelled_sales_invoice(invoice_name):
    """Delete a cancelled invoice and its cancelled ledger rows safely."""
    if frappe.session.user != "Administrator":
        frappe.throw(
            _("Only Administrator can delete cancelled Sales Invoices."),
            frappe.PermissionError,
        )

    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    if invoice.docstatus != 2:
        frappe.throw(_("Only a cancelled Sales Invoice can be deleted."))

    newer_amendment = frappe.db.get_value(
        "Sales Invoice",
        {"amended_from": invoice.name},
        "name",
    )
    if newer_amendment:
        frappe.throw(
            _("Delete amended Sales Invoice {0} first.").format(newer_amendment)
        )

    if frappe.db.exists(
        "Payment Entry Reference",
        {
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice.name,
            "docstatus": 1,
        },
    ):
        frappe.throw(
            _("Sales Invoice {0} is linked to a submitted Payment Entry.").format(
                invoice.name
            )
        )
    if frappe.db.exists("Sales Invoice", {"return_against": invoice.name}):
        frappe.throw(
            _("Sales Invoice {0} has a credit/debit adjustment that must be deleted first.").format(
                invoice.name
            )
        )

    active_bookings = frappe.get_all(
        "Ticket Booking",
        filters={"sales_invoice": invoice.name, "docstatus": ("!=", 2)},
        pluck="name",
    )
    if active_bookings:
        frappe.throw(
            _("Unlink the active Ticket Booking(s) first: {0}").format(
                ", ".join(active_bookings)
            )
        )

    non_cancelled_gl = frappe.db.exists(
        "GL Entry",
        {
            "voucher_type": "Sales Invoice",
            "voucher_no": invoice.name,
            "is_cancelled": 0,
        },
    )
    if non_cancelled_gl:
        frappe.throw(
            _("Sales Invoice {0} still has active General Ledger entries.").format(
                invoice.name
            )
        )

    if frappe.db.exists(
        "Stock Ledger Entry",
        {"voucher_type": "Sales Invoice", "voucher_no": invoice.name},
    ):
        frappe.throw(
            _("Stock-linked Sales Invoices cannot be deleted through this action.")
        )

    # AccountsController normally performs this cleanup only when the global
    # Delete Linked Ledger Entries setting is enabled. Keep that global safety
    # setting unchanged and clean only this already-cancelled invoice here.
    frappe.db.delete(
        "GL Entry",
        {"voucher_type": "Sales Invoice", "voucher_no": invoice.name},
    )
    frappe.db.delete(
        "Payment Ledger Entry",
        {"voucher_type": "Sales Invoice", "voucher_no": invoice.name},
    )
    frappe.db.delete(
        "Payment Ledger Entry",
        {
            "against_voucher_type": "Sales Invoice",
            "against_voucher_no": invoice.name,
            "delinked": 1,
        },
    )

    frappe.delete_doc("Sales Invoice", invoice.name, ignore_permissions=True)
    return invoice.name


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
    if getattr(doc, "is_return", False):
        sync_submitted_credit_note(doc)
        return
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        sync_ticket_booking(booking_name, sales_invoice_name=doc.name)
    for service_name in get_related_visa_services_from_sales_invoice(doc):
        sync_visa_service(service_name, sales_invoice_name=doc.name)
    for order_name in get_related_general_service_orders_from_sales_invoice(doc):
        sync_general_service_order(order_name, sales_invoice_name=doc.name)
    from esrm_travel.customer_document_email import queue_invoice_email
    queue_invoice_email(doc)


def on_update_after_submit_sales_invoice(doc, method=None):
    if getattr(doc, "is_return", False):
        sync_submitted_credit_note(doc)
        return
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        sync_ticket_booking(booking_name, sales_invoice_name=doc.name)
    for service_name in get_related_visa_services_from_sales_invoice(doc):
        sync_visa_service(service_name, sales_invoice_name=doc.name)
    for order_name in get_related_general_service_orders_from_sales_invoice(doc):
        sync_general_service_order(order_name, sales_invoice_name=doc.name)


def on_cancel_sales_invoice(doc, method=None):
    if getattr(doc, "is_return", False):
        sync_cancelled_credit_note(doc)
        return
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        sync_ticket_booking(booking_name, sales_invoice_name=doc.name, clear_sales_invoice=True)
    for service_name in get_related_visa_services_from_sales_invoice(doc):
        sync_visa_service(service_name, sales_invoice_name=doc.name, clear_sales_invoice=True)
    for order_name in get_related_general_service_orders_from_sales_invoice(doc):
        sync_general_service_order(order_name, sales_invoice_name=doc.name, clear_sales_invoice=True)


def sync_submitted_credit_note(doc):
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        if not frappe.db.exists("Ticket Booking", booking_name):
            continue
        frappe.db.set_value(
            "Ticket Booking",
            booking_name,
            {
                "credit_note": doc.name,
                "cancellation_status": "Credit Note Issued",
                "invoice_status": "Credit Note Issued",
                "status": "Cancelled",
            },
            update_modified=True,
        )


def sync_cancelled_credit_note(doc):
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        if not frappe.db.exists("Ticket Booking", booking_name):
            continue
        linked_credit_note = frappe.db.get_value(
            "Ticket Booking", booking_name, "credit_note"
        )
        if linked_credit_note != doc.name:
            continue
        frappe.db.set_value(
            "Ticket Booking",
            booking_name,
            {
                "credit_note": None,
                "cancellation_status": "Active",
                "invoice_status": frappe.db.get_value(
                    "Sales Invoice",
                    frappe.db.get_value("Ticket Booking", booking_name, "sales_invoice"),
                    "status",
                ) or "Not Invoiced",
                "status": "Invoiced",
            },
            update_modified=True,
        )


def after_delete_sales_invoice(doc, method=None):
    if getattr(doc, "is_return", False):
        sync_cancelled_credit_note(doc)
        return
    for booking_name in get_related_ticket_bookings_from_sales_invoice(doc):
        sync_ticket_booking(booking_name, sales_invoice_name=doc.name, clear_sales_invoice=True)
    for service_name in get_related_visa_services_from_sales_invoice(doc):
        sync_visa_service(service_name, sales_invoice_name=doc.name, clear_sales_invoice=True)
    for order_name in get_related_general_service_orders_from_sales_invoice(doc):
        sync_general_service_order(order_name, sales_invoice_name=doc.name, clear_sales_invoice=True)


def on_submit_payment_entry(doc, method=None):
    from esrm_travel.cash_advance import update_due_date_from_payment_entry
    update_due_date_from_payment_entry(doc)
    for booking_name in get_related_ticket_bookings_from_payment_entry(doc):
        sync_ticket_booking(booking_name)
    for service_name in get_related_visa_services_from_payment_entry(doc):
        sync_visa_service(service_name)
    for order_name in get_related_general_service_orders_from_payment_entry(doc):
        sync_general_service_order(order_name)
    from esrm_travel.customer_document_email import queue_money_receipt_email
    queue_money_receipt_email(doc)


def on_update_after_submit_payment_entry(doc, method=None):
    for booking_name in get_related_ticket_bookings_from_payment_entry(doc):
        sync_ticket_booking(booking_name)
    for service_name in get_related_visa_services_from_payment_entry(doc):
        sync_visa_service(service_name)
    for order_name in get_related_general_service_orders_from_payment_entry(doc):
        sync_general_service_order(order_name)


def on_cancel_payment_entry(doc, method=None):
    for booking_name in get_related_ticket_bookings_from_payment_entry(doc):
        sync_ticket_booking(booking_name)
    for service_name in get_related_visa_services_from_payment_entry(doc):
        sync_visa_service(service_name)
    for order_name in get_related_general_service_orders_from_payment_entry(doc):
        sync_general_service_order(order_name)


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


def get_related_visa_services_from_sales_invoice(doc):
    service_names = set()
    if getattr(doc, "esrm_visa_service", None):
        service_names.add(doc.esrm_visa_service)
    for row in doc.get("esrm_visa_services", []):
        if row.visa_service:
            service_names.add(row.visa_service)
    return service_names


def get_related_visa_services_from_payment_entry(doc):
    service_names = set()
    for row in doc.get("references", []):
        if row.reference_doctype != "Sales Invoice" or not row.reference_name:
            continue
        invoice = frappe.get_doc("Sales Invoice", row.reference_name)
        service_names.update(get_related_visa_services_from_sales_invoice(invoice))
    return service_names


def get_related_general_service_orders_from_sales_invoice(doc):
    order_names = set()
    if getattr(doc, "esrm_general_service_order", None):
        order_names.add(doc.esrm_general_service_order)
    for row in doc.get("esrm_general_services", []):
        if row.general_service_order:
            order_names.add(row.general_service_order)
    return order_names


def get_related_general_service_orders_from_payment_entry(doc):
    order_names = set()
    for row in doc.get("references", []):
        if row.reference_doctype == "Sales Invoice" and row.reference_name:
            order_names.update(get_related_general_service_orders_from_sales_invoice(frappe.get_doc("Sales Invoice", row.reference_name)))
    return order_names


def sync_general_service_order(order_name, sales_invoice_name=None, clear_sales_invoice=False):
    if not order_name or not frappe.db.exists("General Service Order", order_name):
        return
    order = frappe.get_doc("General Service Order", order_name)
    if clear_sales_invoice and order.sales_invoice == sales_invoice_name:
        order.sales_invoice = None
        order.invoice_status = "Not Invoiced"
    elif sales_invoice_name and not order.sales_invoice:
        order.sales_invoice = sales_invoice_name
    if not clear_sales_invoice:
        order.sync_invoice_details()
    order.set_status()
    frappe.db.set_value("General Service Order", order.name, {"sales_invoice":order.sales_invoice,"invoice_status":order.invoice_status,"status":order.status}, update_modified=True)


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


def sync_visa_service(service_name, sales_invoice_name=None, clear_sales_invoice=False):
    if not service_name or not frappe.db.exists("Visa Service", service_name):
        return

    service = frappe.get_doc("Visa Service", service_name)
    if clear_sales_invoice and service.sales_invoice == sales_invoice_name:
        service.sales_invoice = None
        service.invoice_status = "Not Invoiced"
        service.paid_amount = 0
        service.outstanding_amount = flt(service.invoice_amount)
    elif sales_invoice_name and not service.sales_invoice:
        service.sales_invoice = sales_invoice_name

    if not clear_sales_invoice:
        service.sync_invoice_details()
    service.set_status()
    frappe.db.set_value(
        "Visa Service",
        service.name,
        {
            "sales_invoice": service.sales_invoice,
            "invoice_status": service.invoice_status,
            "paid_amount": service.paid_amount,
            "outstanding_amount": service.outstanding_amount,
            "status": service.status,
        },
        update_modified=True,
    )
