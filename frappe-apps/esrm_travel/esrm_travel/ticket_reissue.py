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
    "pending_reissued_ticket", "reissued_ticket_number", "reissue_iata_amount",
    "ticket_number_search",
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
        {"fieldname": "reissued_ticket_number", "label": "New / Reissued Ticket Number", "fieldtype": "Data", "insert_after": "original_ticket_number", "read_only": 1, "allow_on_submit": 1, "in_standard_filter": 0, "in_global_search": 1},
        {"fieldname": "ticket_number_search", "label": "Ticket Number", "fieldtype": "Data", "insert_after": "reissued_ticket_number", "read_only": 1, "allow_on_submit": 1, "in_standard_filter": 1, "in_global_search": 1, "depends_on": "eval:0"},
        {"fieldname": "original_flight_date", "label": "Original Flight Date", "fieldtype": "Date", "insert_after": "ticket_number_search", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "original_invoice_amount", "label": "Original Invoice Amount", "fieldtype": "Currency", "insert_after": "original_flight_date", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "original_iata_amount", "label": "Original IATA Amount", "fieldtype": "Currency", "insert_after": "original_invoice_amount", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "reissue_proposed_section", "label": "Proposed Reissue", "fieldtype": "Section Break", "insert_after": "original_iata_amount", "collapsible": 1},
        {"fieldname": "pending_ticket_number", "label": "New Ticket Number", "fieldtype": "Data", "insert_after": "reissue_proposed_section", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_flight_date", "label": "New Flight Date", "fieldtype": "Date", "insert_after": "pending_ticket_number", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_return_date", "label": "New Return Date", "fieldtype": "Date", "insert_after": "pending_flight_date", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_invoice_amount", "label": "Revised Invoice Amount", "fieldtype": "Currency", "insert_after": "pending_return_date", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "reissue_proposed_column", "fieldtype": "Column Break", "insert_after": "pending_invoice_amount"},
        {"fieldname": "pending_iata_amount", "label": "Proposed Reissue IATA Amount", "fieldtype": "Currency", "insert_after": "reissue_proposed_column", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "reissue_iata_amount", "label": "Reissue IATA Amount", "fieldtype": "Currency", "insert_after": "pending_iata_amount", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_reissue_penalty", "label": "Airline Reissue Penalty", "fieldtype": "Currency", "insert_after": "reissue_iata_amount", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_service_fee", "label": "ESRM Reissue Fee", "fieldtype": "Currency", "insert_after": "pending_reissue_penalty", "read_only": 1, "allow_on_submit": 1},
        {"fieldname": "pending_reissued_ticket", "label": "Reissued Ticket", "fieldtype": "Attach", "insert_after": "pending_service_fee", "read_only": 1, "allow_on_submit": 1},
    ]}, update=True)
    obsolete_field = "Ticket Booking-pending_admin_approval"
    if frappe.db.exists("Custom Field", obsolete_field):
        frappe.delete_doc("Custom Field", obsolete_field, ignore_permissions=True, force=True)
    search_fields = "customer,passenger_name,pnr,ticket_number_search,ticket_number,reissued_ticket_number,original_ticket_number,pending_ticket_number,invoice_number,reference,airline,sales_invoice"
    existing = frappe.db.get_value("Property Setter", {
        "doc_type": "Ticket Booking", "doctype_or_field": "DocType", "property": "search_fields",
    })
    if existing:
        frappe.db.set_value("Property Setter", existing, "value", search_fields)
    else:
        frappe.make_property_setter({
            "doctype": "Ticket Booking", "doctype_or_field": "DocType",
            "property": "search_fields", "value": search_fields, "property_type": "Data",
        }, module="ESRM Travel")
    ticket_filter_setter = frappe.db.get_value("Property Setter", {
        "doc_type": "Ticket Booking", "doctype_or_field": "DocField",
        "field_name": "ticket_number", "property": "in_standard_filter",
    })
    if ticket_filter_setter:
        frappe.db.set_value("Property Setter", ticket_filter_setter, "value", "0")
    else:
        frappe.make_property_setter({
            "doctype": "Ticket Booking", "doctype_or_field": "DocField",
            "fieldname": "ticket_number", "property": "in_standard_filter",
            "value": "0", "property_type": "Check",
        }, module="ESRM Travel")
    frappe.db.sql(
        """
        update `tabTicket Booking`
        set ticket_number_search = trim(concat_ws(' ',
            nullif(ticket_number, ''), nullif(reissued_ticket_number, ''),
            nullif(original_ticket_number, ''), nullif(pending_ticket_number, '')
        ))
        """
    )
    frappe.db.sql(
        """
        update `tabTicket Booking`
        set approval_status = 'Pending Approval'
        where reissue_status = 'Pending Approval' and docstatus != 2
        """
    )
    frappe.clear_cache(doctype="Ticket Booking")


def _booking(name, allow_pending_reissue=False):
    booking = frappe.get_doc("Ticket Booking", name)
    booking.check_permission("read")
    is_pending_reissue = (
        allow_pending_reissue
        and booking.reissue_status == "Pending Approval"
        and booking.approval_status == "Pending Approval"
    )
    if booking.docstatus != 1 or (
        booking.approval_status != "Approved" and not is_pending_reissue
    ):
        frappe.throw(_("Only an approved Ticket Booking can be reissued."))
    return booking


@frappe.whitelist()
def find_ticket_booking(ticket_number):
    ticket_number = (ticket_number or "").strip()
    if not ticket_number:
        frappe.throw(_("Enter a ticket number."))
    matches = frappe.get_list(
        "Ticket Booking",
        filters={"docstatus": ["!=", 2]},
        or_filters=[
            ["ticket_number", "=", ticket_number],
            ["reissued_ticket_number", "=", ticket_number],
            ["original_ticket_number", "=", ticket_number],
            ["pending_ticket_number", "=", ticket_number],
        ],
        fields=["name"],
        limit_page_length=2,
    )
    if not matches:
        frappe.throw(_("No Ticket Booking was found for ticket number {0}.").format(ticket_number))
    if len(matches) > 1:
        frappe.throw(_("More than one booking uses ticket number {0}. Please contact Administrator.").format(ticket_number))
    return matches[0].name


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
    if booking.trip_type == "Return" and not (new_return_date or booking.return_date):
        frappe.throw(_("New return date is required for a return trip."))
    if flt(revised_invoice_amount) <= 0:
        frappe.throw(_("Revised invoice amount must be greater than zero."))
    duplicate = frappe.db.exists("Ticket Booking", {
        "ticket_number": new_ticket_number,
        "name": ["!=", booking.name],
        "docstatus": ["!=", 2],
    })
    duplicate = duplicate or frappe.db.exists("Ticket Booking", {
        "reissued_ticket_number": new_ticket_number,
        "name": ["!=", booking.name],
        "docstatus": ["!=", 2],
    })
    if duplicate:
        frappe.throw(_("Ticket number {0} is already used in booking {1}.").format(
            new_ticket_number, duplicate
        ))
    values = {
        "reissue_status": "Pending Approval", "approval_status": "Pending Approval",
        "reissue_requested_by": frappe.session.user,
        "reissue_requested_at": now(), "reissue_reason": reason.strip(),
        "original_ticket_number": booking.ticket_number, "original_flight_date": booking.flight_date,
        "original_invoice_amount": booking.invoice_amount, "original_iata_amount": booking.iata_amount,
        "pending_ticket_number": new_ticket_number, "pending_flight_date": new_flight_date,
        "pending_return_date": new_return_date or booking.return_date,
        "pending_invoice_amount": flt(revised_invoice_amount),
        "pending_iata_amount": flt(revised_iata_amount), "pending_reissue_penalty": flt(reissue_penalty),
        "pending_service_fee": flt(service_fee), "pending_reissued_ticket": attachment,
        "ticket_number_search": " ".join(filter(None, [booking.ticket_number, new_ticket_number])),
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
    booking = _booking(booking_name, allow_pending_reissue=True)
    if booking.reissue_status != "Pending Approval":
        frappe.throw(_("This booking has no pending reissue request."))
    if booking.sales_invoice:
        invoice = frappe.get_doc("Sales Invoice", booking.sales_invoice)
        if invoice.docstatus == 1 and flt(invoice.outstanding_amount) < flt(invoice.grand_total):
            frappe.throw(_("The original invoice is partly or fully paid. Create a customer adjustment before approving this reissue."))
    original_ticket = booking.original_ticket_number or booking.ticket_number
    booking.ticket_number = original_ticket
    booking.reissued_ticket_number = booking.pending_ticket_number
    booking.ticket_number_search = " ".join(filter(None, [original_ticket, booking.pending_ticket_number]))
    booking.flight_date = booking.pending_flight_date
    if booking.trip_type == "Return":
        booking.return_date = booking.pending_return_date or booking.return_date
    booking.invoice_amount = flt(booking.pending_invoice_amount) + flt(booking.pending_service_fee)
    original_iata = flt(booking.original_iata_amount)
    booking.reissue_iata_amount = flt(booking.pending_iata_amount)
    booking.iata_amount = original_iata + booking.reissue_iata_amount
    if booking.pending_reissued_ticket:
        booking.uploaded_ticket = booking.pending_reissued_ticket
    booking.remarks = _("REISSUED from ticket {0} on {1}. {2}").format(
        original_ticket or booking.name, nowdate(), booking.reissue_reason
    )
    booking.amendment_reason = _("Ticket reissued: {0}").format(booking.reissue_reason)
    booking.reissue_status = "Reissued"
    booking.approval_status = "Approved"
    booking.flags.skip_approval_notification = True
    booking.save(ignore_permissions=True)
    _notify(
        booking.reissue_requested_by, booking,
        _("Ticket reissue {0} was approved").format(booking.name),
        _("The reissued ticket and revised invoice are now recorded."),
    )
    return {"booking": booking.name, "invoice": booking.sales_invoice}


@frappe.whitelist()
def bulk_approve_pending_bookings(booking_names):
    """Approve selected initial bookings and/or reissue requests."""
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only Administrator can bulk approve bookings."), frappe.PermissionError)

    names = frappe.parse_json(booking_names) if isinstance(booking_names, str) else booking_names
    approved = []
    failed = []
    for name in dict.fromkeys(names or []):
        savepoint = f"bulk_approve_{len(approved) + len(failed)}"
        frappe.db.savepoint(savepoint)
        try:
            booking = frappe.get_doc("Ticket Booking", name)
            if booking.reissue_status == "Pending Approval":
                approve_ticket_reissue(name)
            elif booking.approval_status == "Pending Approval":
                from frappe.model.workflow import apply_workflow

                apply_workflow(booking, "Approve")
            else:
                frappe.throw(_("No pending approval was found."))
            approved.append(name)
        except Exception as exc:
            frappe.db.rollback(save_point=savepoint)
            failed.append({"booking": name, "error": str(exc)})

    return {"approved": approved, "failed": failed}


@frappe.whitelist()
def bulk_reject_pending_bookings(booking_names, reason=None):
    """Reject selected initial bookings and/or reissue requests."""
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only Administrator can bulk reject bookings."), frappe.PermissionError)

    names = frappe.parse_json(booking_names) if isinstance(booking_names, str) else booking_names
    rejected = []
    failed = []
    for name in dict.fromkeys(names or []):
        savepoint = f"bulk_reject_{len(rejected) + len(failed)}"
        frappe.db.savepoint(savepoint)
        try:
            booking = frappe.get_doc("Ticket Booking", name)
            if booking.reissue_status == "Pending Approval":
                reject_ticket_reissue(name, reason)
            elif booking.approval_status == "Pending Approval":
                from frappe.model.workflow import apply_workflow

                apply_workflow(booking, "Reject")
            else:
                frappe.throw(_("No pending approval was found."))
            rejected.append(name)
        except Exception as exc:
            frappe.db.rollback(save_point=savepoint)
            failed.append({"booking": name, "error": str(exc)})

    return {"rejected": rejected, "failed": failed}


@frappe.whitelist()
def update_reissue_iata_amount(booking_name, amount):
    booking = _booking(booking_name)
    if booking.reissue_status != "Reissued" or booking.payment_mode != "IATA":
        frappe.throw(_("Reissue IATA amount is only available for an approved IATA reissue."))
    if frappe.session.user != "Administrator" and booking.booking_owner != frappe.session.user:
        frappe.throw(_("Only the booking owner or Administrator can enter this cost."), frappe.PermissionError)
    if booking.iata_settlement_status == "Settled" or booking.iata_settlement:
        frappe.throw(_("This ticket is already included in an IATA settlement."))
    reissue_amount = flt(amount)
    if reissue_amount <= 0:
        frappe.throw(_("Reissue IATA amount must be greater than zero."))
    original_iata = flt(booking.original_iata_amount)
    total_iata = original_iata + reissue_amount
    values = {
        "reissue_iata_amount": reissue_amount,
        "pending_iata_amount": reissue_amount,
        "iata_amount": total_iata,
        "net_iata_cost": total_iata - flt(booking.iata_credit_amount),
        "cost_status": "Complete",
        "cost_entered_by_owner": 1,
        "commission": flt(booking.gross_amount) - total_iata,
        "profit": flt(booking.invoice_amount) - total_iata,
    }
    frappe.db.set_value("Ticket Booking", booking.name, values, update_modified=True)
    booking.add_comment("Info", _("Reissue IATA amount updated to {0}.").format(reissue_amount))
    return {"reissue_iata_amount": reissue_amount, "total_iata_amount": total_iata}


def repair_reissue_tracking(booking_name, original_ticket_number, reissued_ticket_number,
    original_iata_amount, reissue_iata_amount):
    booking = _booking(booking_name)
    original_iata = flt(original_iata_amount)
    reissue_iata = flt(reissue_iata_amount)
    total_iata = original_iata + reissue_iata
    values = {
        "ticket_number": original_ticket_number,
        "original_ticket_number": original_ticket_number,
        "pending_ticket_number": reissued_ticket_number,
        "reissued_ticket_number": reissued_ticket_number,
        "ticket_number_search": f"{original_ticket_number} {reissued_ticket_number}",
        "original_iata_amount": original_iata,
        "pending_iata_amount": reissue_iata,
        "reissue_iata_amount": reissue_iata,
        "iata_amount": total_iata,
        "net_iata_cost": total_iata - flt(booking.iata_credit_amount),
        "cost_status": "Complete",
        "cost_entered_by_owner": 1,
        "commission": flt(booking.gross_amount) - total_iata,
        "profit": flt(booking.invoice_amount) - total_iata,
    }
    frappe.db.set_value("Ticket Booking", booking.name, values, update_modified=True)
    booking.add_comment("Info", _("Original and reissue ticket/IATA details corrected."))
    return {"booking": booking.name, "original_iata": original_iata,
        "reissue_iata": reissue_iata, "total_iata": total_iata}


def repair_reissue_invoice(booking_name):
    """Apply the separate reissue fee to an already-approved unpaid reissue."""
    booking = _booking(booking_name)
    if booking.reissue_status != "Reissued":
        frappe.throw(_("Booking {0} is not an approved reissue.").format(booking.name))
    expected_total = flt(booking.pending_invoice_amount) + flt(booking.pending_service_fee)
    if expected_total <= 0:
        frappe.throw(_("No revised invoice amount is recorded."))
    if booking.sales_invoice:
        invoice = frappe.get_doc("Sales Invoice", booking.sales_invoice)
        if invoice.docstatus == 1 and flt(invoice.outstanding_amount) < flt(invoice.grand_total):
            frappe.throw(_("The reissued invoice is partly or fully paid and cannot be replaced automatically."))
    if flt(booking.invoice_amount) != expected_total:
        booking.invoice_amount = expected_total
        booking.amendment_reason = _("Add separately recorded ESRM reissue fee")
        booking.save(ignore_permissions=True)
    return {"booking": booking.name, "invoice": booking.sales_invoice, "total": expected_total}


@frappe.whitelist()
def reject_ticket_reissue(booking_name, reason=None):
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only Administrator can reject a ticket reissue."), frappe.PermissionError)
    booking = _booking(booking_name)
    if booking.reissue_status != "Pending Approval":
        frappe.throw(_("This booking has no pending reissue request."))
    frappe.db.set_value(
        "Ticket Booking",
        booking.name,
        {"reissue_status": "Rejected", "approval_status": "Approved"},
        update_modified=True,
    )
    booking.add_comment("Info", _("Ticket reissue rejected. {0}").format(reason or ""))
    _notify(
        booking.reissue_requested_by, booking,
        _("Ticket reissue {0} was rejected").format(booking.name),
        reason or _("Please review the booking with Administrator."),
    )
    return booking.name
