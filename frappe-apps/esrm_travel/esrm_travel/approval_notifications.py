from html import escape

import frappe
from frappe import _
from frappe.utils import get_url_to_form

from esrm_travel.access_control import APPROVER_ROLE


NOTIFIABLE_STATES = {"Pending Approval", "Approved", "Rejected"}


def notify_ticket_booking_approval(doc, method=None):
    """Notify the next participants when a booking changes approval state."""
    previous = doc.get_doc_before_save()
    previous_state = previous.approval_status if previous else None
    current_state = doc.approval_status

    if current_state == previous_state or current_state not in NOTIFIABLE_STATES:
        return

    recipients = _get_recipients(doc, current_state)
    if not recipients:
        return

    subject, message = _get_message(doc, current_state)
    document_url = get_url_to_form(doc.doctype, doc.name)

    for user in recipients:
        _create_in_app_notification(user, doc, subject, message, document_url)


def notify_service_approval(doc, method=None):
    """Use the established approval routing for ticket and visa service records."""
    notify_ticket_booking_approval(doc, method)


def notify_ticket_cost_entered(doc, method=None):
    previous = doc.get_doc_before_save()
    if (
        frappe.session.user == "Administrator"
        or frappe.session.user != doc.booking_owner
        or not previous
    ):
        return

    cost_field = "iata_amount" if doc.payment_mode == "IATA" else "supplier_cost"
    if not doc.has_value_changed(cost_field):
        return

    cost_label = doc.meta.get_label(cost_field)
    subject = _("Cost updated for Ticket Booking {0}").format(doc.name)
    message = _(
        "{0} updated {1} for approved ticket booking {2}."
    ).format(doc.booking_owner, cost_label, doc.name)
    _create_in_app_notification(
        "Administrator",
        doc,
        subject,
        message,
        get_url_to_form(doc.doctype, doc.name),
    )


def _get_recipients(doc, state):
    if state == "Pending Approval":
        users = frappe.get_all(
            "Has Role",
            filters={
                "role": APPROVER_ROLE,
                "parenttype": "User",
                "parent": ["!=", "Administrator"],
            },
            pluck="parent",
        )
        users.append("Administrator")
    else:
        owner = getattr(doc, "booking_owner", None) or getattr(doc, "service_owner", None)
        users = [owner] if owner else []

    return sorted(
        {
            user
            for user in users
            if user
            and user != "Guest"
            and user != frappe.session.user
            and frappe.db.get_value("User", user, "enabled")
        }
    )


def _get_message(doc, state):
    if doc.doctype == "Visa Service":
        subject_name = doc.applicant_name or doc.name
        label = _("Visa Service")
    elif doc.doctype == "General Service Order":
        subject_name = doc.subject or doc.name
        label = _("General Service Order")
    else:
        subject_name = doc.passenger_name or doc.name
        label = _("Ticket Booking")
    if state == "Pending Approval":
        return (
            _("{0} {1} requires approval").format(label, doc.name),
            _("{0} {1} for {2} was submitted and is waiting for your approval.").format(
                label, doc.name, subject_name
            ),
        )

    return (
        _("{0} {1} was {2}").format(label, doc.name, state.lower()),
        _("Your {0} {1} for {2} was {3}.").format(
            label.lower(), doc.name, subject_name, state.lower()
        ),
    )


def _create_in_app_notification(user, doc, subject, message, document_url):
    notification = frappe.new_doc("Notification Log")
    notification.update(
        {
            "type": "Alert",
            "for_user": user,
            "from_user": frappe.session.user,
            "subject": subject,
            "email_content": escape(message),
            "document_type": doc.doctype,
            "document_name": doc.name,
            "link": document_url,
        }
    )
    notification.insert(ignore_permissions=True)
