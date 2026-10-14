import re
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import fmt_money, formatdate, get_url_to_form


ALLOWED_DOCTYPES = {
    "Ticket Booking",
    "Visa Service",
    "Employee Advance",
    "Expense Claim",
    "Sales Invoice",
}


def _normalise_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("01") and len(digits) == 11:
        digits = f"88{digits}"
    return digits if len(digits) >= 8 else ""


def _user_phone(user):
    if not user or not frappe.db.exists("User", user):
        return ""
    return _normalise_phone(frappe.db.get_value("User", user, "mobile_no"))


def _employee_phone(employee):
    if not employee:
        return ""
    meta = frappe.get_meta("Employee")
    for fieldname in ("cell_number", "personal_mobile_no", "phone"):
        if meta.has_field(fieldname):
            phone = _normalise_phone(frappe.db.get_value("Employee", employee, fieldname))
            if phone:
                return phone
    user = frappe.db.get_value("Employee", employee, "user_id")
    return _user_phone(user)


def _customer_phone(customer):
    if not customer:
        return ""
    customer_meta = frappe.get_meta("Customer")
    for fieldname in ("mobile_no", "phone"):
        if customer_meta.has_field(fieldname):
            phone = _normalise_phone(frappe.db.get_value("Customer", customer, fieldname))
            if phone:
                return phone
    result = frappe.db.sql(
        """
        select coalesce(nullif(c.mobile_no, ''), nullif(c.phone, ''))
        from `tabContact` c
        inner join `tabDynamic Link` dl
            on dl.parent = c.name and dl.parenttype = 'Contact'
        where dl.link_doctype = 'Customer'
          and dl.link_name = %(customer)s
          and (ifnull(c.mobile_no, '') != '' or ifnull(c.phone, '') != '')
        order by c.is_primary_contact desc, c.modified desc
        limit 1
        """,
        {"customer": customer},
    )
    return _normalise_phone(result[0][0]) if result else ""


def _payload(phone, recipient, message, operator_note=None):
    phone = _normalise_phone(phone)
    return {
        "phone": phone,
        "recipient": recipient,
        "message": message,
        "url": f"https://wa.me/{phone}?text={quote(message)}" if phone else "",
        "operator_note": operator_note or "",
    }


def _internal_message(doc, heading, details):
    return "\n".join([heading, *details, f"Open in ESRM: {get_url_to_form(doc.doctype, doc.name)}"])


def _ticket_payload(doc, event):
    event = event or "workflow"
    pending = event in {"reissue_requested", "void_requested"} or doc.approval_status == "Pending Approval"
    if pending:
        request_type = "Ticket approval"
        if event == "reissue_requested":
            request_type = "Ticket reissue approval"
        elif event == "void_requested":
            request_type = "Ticket void approval"
        message = _internal_message(doc, f"{request_type} required", [
            f"Booking: {doc.name}",
            f"Passenger: {doc.passenger_name}",
            f"Ticket: {doc.ticket_number or 'Not entered'}",
            f"Amount: {fmt_money(doc.invoice_amount or doc.gross_amount, currency='BDT')}",
        ])
        return _payload(_user_phone("Administrator"), "Administrator", message)

    customer_phone = _customer_phone(doc.customer)
    if event in {"reissue_approved", "void_approved"} or doc.approval_status == "Approved":
        status = "approved"
        if event == "reissue_approved":
            status = "reissued"
        elif event == "void_approved":
            status = "voided"
        message = "\n".join([
            f"Dear {doc.customer or 'Customer'},",
            f"Your ticket booking has been {status}.",
            f"Passenger: {doc.passenger_name}",
            f"Ticket: {doc.reissued_ticket_number or doc.ticket_number or 'Not entered'}",
            f"Route: {doc.route_summary or 'Not entered'}",
            f"Flight date: {formatdate(doc.flight_date, 'dd MMM yyyy') if doc.flight_date else 'Not entered'}",
            "Regards, ESRM",
        ])
        return _payload(
            customer_phone,
            doc.customer or "Customer",
            message,
            _("Attach the ticket document in WhatsApp before sending, when applicable."),
        )

    owner = doc.booking_owner
    message = _internal_message(doc, "Ticket booking update", [
        f"Booking: {doc.name}",
        f"Passenger: {doc.passenger_name}",
        f"Status: {doc.approval_status}",
    ])
    return _payload(_user_phone(owner), owner, message)


def _visa_payload(doc, event):
    if doc.approval_status == "Pending Approval":
        message = _internal_message(doc, "Visa service approval required", [
            f"Visa service: {doc.name}",
            f"Applicant: {doc.applicant_name}",
            f"Destination: {doc.destination_country}",
            f"Amount: {fmt_money(doc.invoice_amount, currency=doc.currency or 'BDT')}",
        ])
        return _payload(_user_phone("Administrator"), "Administrator", message)

    phone = _normalise_phone(doc.contact_number) or _customer_phone(doc.customer)
    message = "\n".join([
        f"Dear {doc.applicant_name},",
        f"Your visa service request {doc.name} was {doc.approval_status.lower()}.",
        f"Destination: {doc.destination_country}",
        "Regards, ESRM",
    ])
    return _payload(phone, doc.applicant_name, message)


def _employee_document_payload(doc, event):
    state = getattr(doc, "workflow_state", None) or getattr(doc, "approval_status", None) or "Updated"
    amount = getattr(doc, "advance_amount", None) or getattr(doc, "total_claimed_amount", None) or 0
    if state in {"Pending Approval", "Accounts Review"}:
        message = _internal_message(doc, f"{doc.doctype} approval required", [
            f"Document: {doc.name}",
            f"Employee: {doc.employee_name}",
            f"Amount: {fmt_money(amount, currency=getattr(doc, 'currency', None) or 'BDT')}",
        ])
        return _payload(_user_phone("Administrator"), "Administrator", message)

    phone = _employee_phone(doc.employee)
    message = "\n".join([
        f"Dear {doc.employee_name},",
        f"Your {doc.doctype.lower()} {doc.name} was {state.lower()}.",
        f"Amount: {fmt_money(amount, currency=getattr(doc, 'currency', None) or 'BDT')}",
        "Regards, ESRM",
    ])
    return _payload(phone, doc.employee_name, message)


def _invoice_payload(doc, event):
    phone = _normalise_phone(getattr(doc, "contact_mobile", None)) or _customer_phone(doc.customer)
    display_number = doc.get("esrm_invoice_number") or doc.name
    message = "\n".join([
        f"Dear {doc.customer_name or doc.customer},",
        f"Invoice {display_number} has been issued.",
        f"Date: {formatdate(doc.posting_date, 'dd MMM yyyy')}",
        f"Amount: {fmt_money(doc.grand_total, currency=doc.currency or 'BDT')}",
        "A PDF copy has also been sent to your registered email address.",
        "Regards, ESRM",
    ])
    return _payload(
        phone,
        doc.customer_name or doc.customer,
        message,
        _("Attach the invoice PDF manually if the customer needs it in WhatsApp."),
    )


def _build_payload(doc, event=None):
    if doc.doctype == "Ticket Booking":
        return _ticket_payload(doc, event)
    if doc.doctype == "Visa Service":
        return _visa_payload(doc, event)
    if doc.doctype in {"Employee Advance", "Expense Claim"}:
        return _employee_document_payload(doc, event)
    if doc.doctype == "Sales Invoice":
        return _invoice_payload(doc, event)
    frappe.throw(_("WhatsApp preparation is not supported for {0}.").format(doc.doctype))


@frappe.whitelist()
def get_manual_whatsapp_payload(doctype, name, event=None):
    if doctype not in ALLOWED_DOCTYPES:
        frappe.throw(_("WhatsApp preparation is not supported for {0}.").format(doctype))
    doc = frappe.get_doc(doctype, name)
    doc.check_permission("read")
    return _build_payload(doc, event)


@frappe.whitelist()
def get_manual_whatsapp_payloads(doctype, names, event=None):
    names = frappe.parse_json(names) if isinstance(names, str) else names
    if not isinstance(names, list) or not names or len(names) > 100:
        frappe.throw(_("Select between 1 and 100 records."))
    return [get_manual_whatsapp_payload(doctype, name, event) for name in names]
