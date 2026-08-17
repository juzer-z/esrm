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


def notify_ticket_cost_entered(doc, method=None):
    previous = doc.get_doc_before_save()
    if (
        frappe.session.user == "Administrator"
        or frappe.session.user != doc.booking_owner
        or not doc.cost_entered_by_owner
        or (previous and previous.cost_entered_by_owner)
    ):
        return

    cost_field = "iata_amount" if doc.payment_mode == "IATA" else "supplier_cost"
    cost_label = doc.meta.get_label(cost_field)
    subject = _("Cost entered for Ticket Booking {0}").format(doc.name)
    message = _(
        "{0} entered {1} for approved ticket booking {2}. The cost is now locked for the booking owner."
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
        users = [doc.booking_owner] if doc.booking_owner else []

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
    passenger = doc.passenger_name or doc.name
    if state == "Pending Approval":
        return (
            _("Ticket Booking {0} requires approval").format(doc.name),
            _("Ticket booking {0} for {1} was submitted and is waiting for your approval.").format(
                doc.name, passenger
            ),
        )

    return (
        _("Ticket Booking {0} was {1}").format(doc.name, state.lower()),
        _("Your ticket booking {0} for {1} was {2}.").format(
            doc.name, passenger, state.lower()
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
