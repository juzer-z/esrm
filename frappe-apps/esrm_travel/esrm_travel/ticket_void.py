from html import escape

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import flt, get_url_to_form, now, nowdate


def setup_ticket_void():
    create_custom_fields(
        {
            "Ticket Booking": [
                {"fieldname": "void_section", "label": "Ticket Void", "fieldtype": "Section Break", "insert_after": "pending_reissued_ticket", "collapsible": 1},
                {"fieldname": "void_status", "label": "Void Status", "fieldtype": "Select", "options": "Not Requested\nPending Approval\nVoided\nRejected", "default": "Not Requested", "insert_after": "void_section", "read_only": 1, "allow_on_submit": 1, "in_standard_filter": 1},
                {"fieldname": "void_requested_by", "label": "Requested By", "fieldtype": "Link", "options": "User", "insert_after": "void_status", "read_only": 1, "allow_on_submit": 1},
                {"fieldname": "void_requested_at", "label": "Requested At", "fieldtype": "Datetime", "insert_after": "void_requested_by", "read_only": 1, "allow_on_submit": 1},
                {"fieldname": "void_reason", "label": "Void Reason", "fieldtype": "Small Text", "insert_after": "void_requested_at", "read_only": 1, "allow_on_submit": 1},
                {"fieldname": "void_column", "fieldtype": "Column Break", "insert_after": "void_reason"},
                {"fieldname": "void_approved_by", "label": "Approved By", "fieldtype": "Link", "options": "User", "insert_after": "void_column", "read_only": 1, "allow_on_submit": 1},
                {"fieldname": "void_approved_at", "label": "Approved At", "fieldtype": "Datetime", "insert_after": "void_approved_by", "read_only": 1, "allow_on_submit": 1},
                {"fieldname": "void_original_invoice", "label": "Original Sales Invoice", "fieldtype": "Link", "options": "Sales Invoice", "insert_after": "void_approved_at", "read_only": 1, "allow_on_submit": 1},
                {"fieldname": "void_original_invoice_amount", "label": "Original Invoice Amount", "fieldtype": "Currency", "insert_after": "void_original_invoice", "read_only": 1, "allow_on_submit": 1},
                {"fieldname": "void_original_cost", "label": "Original Ticket Cost", "fieldtype": "Currency", "insert_after": "void_original_invoice_amount", "read_only": 1, "allow_on_submit": 1},
            ]
        },
        update=True,
    )
    frappe.clear_cache(doctype="Ticket Booking")


def _notify(user, booking, subject, message):
    if not user or user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
        return
    notification = frappe.new_doc("Notification Log")
    notification.update(
        {
            "type": "Alert",
            "for_user": user,
            "from_user": frappe.session.user,
            "subject": subject,
            "email_content": escape(message),
            "document_type": booking.doctype,
            "document_name": booking.name,
            "link": get_url_to_form(booking.doctype, booking.name),
        }
    )
    notification.insert(ignore_permissions=True)


@frappe.whitelist()
def request_ticket_void(booking_name, reason, requested_by=None):
    booking = frappe.get_doc("Ticket Booking", booking_name)
    booking.check_permission("read")
    requester = requested_by if frappe.session.user == "Administrator" and requested_by else frappe.session.user
    if booking.docstatus != 1 or booking.approval_status != "Approved":
        frappe.throw(_("Only an approved booking can be submitted for void approval."))
    if frappe.session.user != "Administrator" and (
        "ESRM Agent" not in frappe.get_roles() or booking.booking_owner != frappe.session.user
    ):
        frappe.throw(_("Only the booking agent can request a void."), frappe.PermissionError)
    if booking.void_status == "Pending Approval":
        frappe.throw(_("This ticket already has a pending void request."))
    if booking.void_status == "Voided":
        frappe.throw(_("This ticket is already voided."))
    if not (reason or "").strip():
        frappe.throw(_("Void reason is required."))
    if booking.reissue_status == "Pending Approval":
        frappe.throw(_("Resolve the pending reissue request before voiding this ticket."))

    original_cost = flt(booking.iata_amount) if booking.payment_mode == "IATA" else flt(booking.supplier_cost)
    frappe.db.set_value(
        "Ticket Booking",
        booking.name,
        {
            "void_status": "Pending Approval",
            "void_requested_by": requester,
            "void_requested_at": now(),
            "void_reason": reason.strip(),
            "void_original_invoice": booking.sales_invoice,
            "void_original_invoice_amount": flt(booking.invoice_amount),
            "void_original_cost": original_cost,
            "approval_status": "Pending Approval",
        },
        update_modified=True,
    )
    _notify(
        "Administrator",
        booking,
        _("Ticket void {0} requires approval").format(booking.name),
        _("{0} requested a no-charge void for ticket {1}. Reason: {2}").format(
            booking.passenger_name, booking.ticket_number, reason.strip()
        ),
    )
    booking.add_comment("Info", _("No-charge ticket void submitted for Administrator approval."))
    return booking.name


def _make_zero_void_invoice(booking, original_invoice):
    original_invoice.cancel()
    void_invoice = frappe.copy_doc(original_invoice)
    void_invoice.name = None
    void_invoice.docstatus = 0
    void_invoice.amended_from = original_invoice.name
    void_invoice.posting_date = nowdate()
    void_invoice.due_date = nowdate()
    void_invoice.remarks = _("VOIDED TICKET - ZERO PAYABLE. Ticket Booking {0}. Reason: {1}").format(
        booking.name, booking.void_reason
    )
    for item in void_invoice.items:
        item.rate = 0
        item.amount = 0
        item.net_rate = 0
        item.net_amount = 0
        item.base_rate = 0
        item.base_amount = 0
        item.base_net_rate = 0
        item.base_net_amount = 0
        item.description = _("VOIDED TICKET - ZERO PAYABLE\n{0}").format(item.description or "")
    for row in void_invoice.get("esrm_ticket_bookings") or []:
        row.fare = 0
        row.remarks = _("VOIDED - ZERO PAYABLE")
    void_invoice.flags.ignore_permissions = True
    void_invoice.insert()
    void_invoice.submit()
    return void_invoice.name


@frappe.whitelist()
def approve_ticket_void(booking_name):
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only Administrator can approve a ticket void."), frappe.PermissionError)
    booking = frappe.get_doc("Ticket Booking", booking_name)
    if booking.void_status != "Pending Approval":
        frappe.throw(_("This booking has no pending void request."))
    if booking.iata_settlement or booking.iata_settlement_status == "Settled":
        frappe.throw(_("Remove this ticket from its IATA settlement before voiding it."))
    if not booking.sales_invoice:
        frappe.throw(_("The booking has no linked Sales Invoice."))
    invoice = frappe.get_doc("Sales Invoice", booking.sales_invoice)
    if invoice.docstatus != 1 or invoice.is_return:
        frappe.throw(_("The linked Sales Invoice must be a submitted standard invoice."))
    if abs(flt(invoice.outstanding_amount) - flt(invoice.grand_total)) > 0.01:
        frappe.throw(_("The linked Sales Invoice has a payment or allocation and cannot be voided."))

    void_invoice_name = _make_zero_void_invoice(booking, invoice)
    frappe.db.set_value(
        "Ticket Booking",
        booking.name,
        {
            "void_status": "Voided",
            "void_approved_by": frappe.session.user,
            "void_approved_at": now(),
            "approval_status": "Approved",
            "status": "Cancelled",
            "cancellation_status": "Voided",
            "cancellation_date": nowdate(),
            "cancellation_reason": booking.void_reason,
            "gross_amount": 0,
            "invoice_amount": 0,
            "iata_amount": 0,
            "supplier_cost": 0,
            "commission": 0,
            "discount": 0,
            "profit": 0,
            "paid_amount": 0,
            "outstanding_amount": 0,
            "cost_status": "Complete",
            "sales_invoice": void_invoice_name,
            "invoice_status": "Paid",
            "remarks": _("VOIDED - ZERO PAYABLE. {0}").format(booking.void_reason),
        },
        update_modified=True,
    )
    booking.add_comment(
        "Info",
        _("Ticket void approved. Original invoice {0} was cancelled and replaced by zero-payable invoice {1}.").format(
            invoice.name, void_invoice_name
        ),
    )
    _notify(
        booking.void_requested_by,
        booking,
        _("Ticket void {0} was approved").format(booking.name),
        _("Ticket {0} is voided with zero payable and zero ticket cost.").format(booking.ticket_number),
    )
    return {"booking": booking.name, "invoice": void_invoice_name}


@frappe.whitelist()
def reject_ticket_void(booking_name, reason=None):
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only Administrator can reject a ticket void."), frappe.PermissionError)
    booking = frappe.get_doc("Ticket Booking", booking_name)
    if booking.void_status != "Pending Approval":
        frappe.throw(_("This booking has no pending void request."))
    frappe.db.set_value(
        "Ticket Booking",
        booking.name,
        {"void_status": "Rejected", "approval_status": "Approved"},
        update_modified=True,
    )
    _notify(
        booking.void_requested_by,
        booking,
        _("Ticket void {0} was rejected").format(booking.name),
        reason or _("Administrator rejected the ticket void request."),
    )
    return booking.name
