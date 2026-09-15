from html import escape

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import flt, get_url_to_form, now, nowdate


REISSUE_FIELDS = {
    "reissue_status", "reissue_requested_by", "reissue_requested_at",
    "reissue_reason", "original_ticket_number", "original_flight_date",
    "original_invoice_amount", "original_iata_amount", "pending_ticket_number",
    "pending_flight_date", "pending_return_date", "pending_invoice_amount",
    "pending_iata_amount", "pending_reissue_penalty", "pending_service_fee",
    "pending_reissued_ticket",
}


def setup_ticket_reissue():
    create_custom_fields({"Ticket Booking": [
        {"fieldname": "reissue_section", "label": "Ticket Reissue", "fieldtype": "Section Break", "insert_after": "uploaded_ticket", "collapsible": 1},
        {"fieldname": "reissue_status", "label": "Reissue Status", "fieldtype": "Select", "options": "Not Requested\nPending Approval\nReissued\nRejected", "default": "Not Requested", "insert_after": "reissue_section", "read_only": 1, "allow_on_submit": 1, "in_standard_filter": 1},
        {"fieldname": "reissue_requested_by", "label": "Requested By", "fieldtype": "Link", "options": "User", "insert_after": "reissue_status", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "reissue_requested_at", "label": "Requested At", "fieldtype": "Datetime", "insert_after": "reissue_requested_by", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "reissue_reason", "label": "Reissue Reason", "fieldtype": "Small Text", "insert_after": "reissue_requested_at", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "reissue_original_column", "fieldtype": "Column Break", "insert_after": "reissue_reason"},
        {"fieldname": "original_ticket_number", "label": "Original Ticket Number", "fieldtype": "Data", "insert_after": "reissue_original_column", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "original_flight_date", "label": "Original Flight Date", "fieldtype": "Date", "insert_after": "original_ticket_number", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "original_invoice_amount", "label": "Original Invoice Amount", "fieldtype": "Currency", "insert_after": "original_flight_date", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "original_iata_amount", "label": "Original IATA Amount", "fieldtype": "Currency", "insert_after": "original_invoice_amount", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "reissue_proposed_section", "label": "Proposed Reissue", "fieldtype": "Section Break", "insert_after": "original_iata_amount", "collapsible": 1},
        {"fieldname": "pending_ticket_number", "label": "New Ticket Number", "fieldtype": "Data", "insert_after": "reissue_proposed_section", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_flight_date", "label": "New Flight Date", "fieldtype": "Date", "insert_after": "pending_ticket_number", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_return_date", "label": "New Return Date", "fieldtype": "Date", "insert_after": "pending_flight_date", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_invoice_amount", "label": "Revised Invoice Amount", "fieldtype": "Currency", "insert_after": "pending_return_date", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "reissue_proposed_column", "fieldtype": "Column Break", "insert_after": "pending_invoice_amount"},
        {"fieldname": "pending_iata_amount", "label": "Revised IATA Amount", "fieldtype": "Currency", "insert_after": "reissue_proposed_column", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_reissue_penalty", "label": "Airline Reissue Penalty", "fieldtype": "Currency", "insert_after": "pending_iata_amount", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_service_fee", "label": "ESRM Reissue Fee", "fieldtype": "Currency", "insert_after": "pending_reissue_penalty", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_reissued_ticket", "label": "Reissued Ticket", "fieldtype": "Attach", "insert_after": "pending_service_fee", "read_only": 1, "allow_on_submit": 1},
    ]}, update=True)
    frappe.clear_cache(doctype="Ticket Booking")


def _booking(name):
    booking = frappe.get_doc("Ticket Booking", name)
    booking.check_permission("read")
    if booking.docstatus != 1 or booking.approval_status != "Approved":
        frappe.throw(_("Only an approved Ticket Booking can be reissued."))
    return booking


def _notify(user, booking, subject, message):
    if not user or user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
        return
    notification = frappe.new_doc("Notification Log")
    notification.update({
        "type": "Alert",
        "for_user": user,
        "from_user": frappe.session.user,
        "subject": subject,
        "email_content": escape(message),
        "document_type": booking.doctype,
        "document_name": booking.name,
        "link": get_url_to_form(booking.doctype, booking.name),
    })
    notification.insert(ignore_permissions=True)


@frappe.whitelist()
def request_ticket_reissue(booking_name, new_ticket_number, new_flight_date,
    revised_invoice_amount, revised_iata_amount=0, new_return_date=None,
    reissue_penalty=0, service_fee=0, reason=None, attachment=None):
    booking = _booking(booking_name)
    roles = set(frappe.get_roles())
    if frappe.session.user != "Administrator" and "ESRM Agent" not in roles:
        frappe.throw(_("Only an agent can prepare a ticket reissue."), frappe.PermissionError)
    if frappe.session.user != "Administrator" and booking.booking_owner != frappe.session.user:
        frappe.throw(_("You can only reissue a booking assigned to you."), frappe.PermissionError)
    if booking.reissue_status == "Pending Approval":
        frappe.throw(_("A reissue request is already pending approval."))
    if not new_ticket_number or not new_flight_date or not (reason or "").strip():
        frappe.throw(_("New ticket number, new flight date and reason are required."))
    if flt(revised_invoice_amount) <= 0:
        frappe.throw(_("Revised invoice amount must be greater than zero."))
    duplicate = frappe.db.exists("Ticket Booking", {
        "ticket_number": new_ticket_number,
        "name": ["!=", booking.name],
        "docstatus": ["!=", 2],
    })
    if duplicate:
        frappe.throw(_("Ticket number {0} is already used in booking {1}.").format(
            new_ticket_number, duplicate
        ))
    values = {
        "reissue_status": "Pending Approval", "reissue_requested_by": frappe.session.user,
        "reissue_requested_at": now(), "reissue_reason": reason.strip(),
        "original_ticket_number": booking.ticket_number, "original_flight_date": booking.flight_date,
        "original_invoice_amount": booking.invoice_amount, "original_iata_amount": booking.iata_amount,
        "pending_ticket_number": new_ticket_number, "pending_flight_date": new_flight_date,
        "pending_return_date": new_return_date, "pending_invoice_amount": flt(revised_invoice_amount),
        "pending_iata_amount": flt(revised_iata_amount), "pending_reissue_penalty": flt(reissue_penalty),
        "pending_service_fee": flt(service_fee), "pending_reissued_ticket": attachment,
    }
    frappe.db.set_value("Ticket Booking", booking.name, values, update_modified=True)
    booking.add_comment("Info", _("Ticket reissue submitted for Administrator approval."))
    _notify(
        "Administrator", booking,
        _("Ticket reissue {0} requires approval").format(booking.name),
        _("{0} requested reissue of ticket {1} to {2}.").format(
            booking.passenger_name, booking.ticket_number, new_ticket_number
        ),
    )
    return booking.name


@frappe.whitelist()
def approve_ticket_reissue(booking_name):
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only Administrator can approve a ticket reissue."), frappe.PermissionError)
    booking = _booking(booking_name)
    if booking.reissue_status != "Pending Approval":
        frappe.throw(_("This booking has no pending reissue request."))
    if booking.sales_invoice:
        invoice = frappe.get_doc("Sales Invoice", booking.sales_invoice)
        if invoice.docstatus == 1 and flt(invoice.outstanding_amount) < flt(invoice.grand_total):
            frappe.throw(_("The original invoice is partly or fully paid. Create a customer adjustment before approving this reissue."))
    original_ticket = booking.ticket_number
    booking.ticket_number = booking.pending_ticket_number
    booking.flight_date = booking.pending_flight_date
    if booking.trip_type == "Return":
        booking.return_date = booking.pending_return_date
    booking.invoice_amount = booking.pending_invoice_amount
    booking.iata_amount = booking.pending_iata_amount
    if booking.pending_reissued_ticket:
        booking.uploaded_ticket = booking.pending_reissued_ticket
    booking.remarks = _("REISSUED from ticket {0} on {1}. {2}").format(
        original_ticket or booking.name, nowdate(), booking.reissue_reason
    )
    booking.amendment_reason = _("Ticket reissued: {0}").format(booking.reissue_reason)
    booking.reissue_status = "Reissued"
    booking.save(ignore_permissions=True)
    _notify(
        booking.reissue_requested_by, booking,
        _("Ticket reissue {0} was approved").format(booking.name),
        _("The reissued ticket and revised invoice are now recorded."),
    )
    return {"booking": booking.name, "invoice": booking.sales_invoice}


@frappe.whitelist()
def reject_ticket_reissue(booking_name, reason=None):
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only Administrator can reject a ticket reissue."), frappe.PermissionError)
    booking = _booking(booking_name)
    if booking.reissue_status != "Pending Approval":
        frappe.throw(_("This booking has no pending reissue request."))
    frappe.db.set_value("Ticket Booking", booking.name, "reissue_status", "Rejected", update_modified=True)
    booking.add_comment("Info", _("Ticket reissue rejected. {0}").format(reason or ""))
    _notify(
        booking.reissue_requested_by, booking,
        _("Ticket reissue {0} was rejected").format(booking.name),
        reason or _("Please review the booking with Administrator."),
    )
    return booking.name
