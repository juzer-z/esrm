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

    if _outgoing_email_is_configured():
        _queue_email_notifications(
            recipients, doc.name, subject, message, document_url
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


def _outgoing_email_is_configured():
    return bool(
        frappe.db.exists(
            "Email Account",
            {
                "enable_outgoing": 1,
                "default_outgoing": 1,
            },
        )
    )


def _queue_email_notifications(users, document_name, subject, message, document_url):
    recipients = [
        email
        for email in frappe.get_all(
            "User",
            filters={"name": ["in", users], "enabled": 1},
            pluck="email",
        )
        if email
    ]
    if not recipients:
        return

    button = (
        '<p><a href="{url}" style="background:#0b7285;color:#fff;'
        'padding:10px 16px;text-decoration:none;border-radius:4px;">'
        "{label}</a></p>"
    ).format(url=escape(document_url, quote=True), label=_("Open Ticket Booking"))

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=f"<p>{escape(message)}</p>{button}",
        reference_doctype="Ticket Booking",
        reference_name=document_name,
    )
