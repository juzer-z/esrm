from html import escape

import frappe
from frappe.utils import get_url, strip_html


def queue_notification_email(doc, method=None):
    """Queue an email copy of every user-facing in-app notification."""
    if not doc.for_user or doc.for_user == "Guest":
        return
    if not _outgoing_email_is_configured():
        return

    frappe.enqueue(
        "esrm_travel.notification_email.send_notification_email",
        queue="short",
        enqueue_after_commit=True,
        notification_name=doc.name,
    )


def send_notification_email(notification_name):
    notification = frappe.get_doc("Notification Log", notification_name)
    user = frappe.db.get_value(
        "User",
        notification.for_user,
        ["email", "enabled"],
        as_dict=True,
    )
    if not user or not user.enabled or not user.email:
        return
    if not _outgoing_email_is_configured():
        return

    subject = strip_html(notification.subject or "ERPNext Notification").strip()
    content = notification.email_content or notification.subject or ""
    document_url = _get_notification_url(notification)
    open_button = ""
    if document_url:
        open_button = (
            '<p><a href="{url}" style="background:#0b7285;color:#fff;'
            'padding:10px 16px;text-decoration:none;border-radius:4px;">'
            "Open in ERPNext</a></p>"
        ).format(url=escape(document_url, quote=True))

    frappe.sendmail(
        recipients=[user.email],
        subject=subject,
        message=f"{content}{open_button}",
        reference_doctype=notification.document_type or None,
        reference_name=notification.document_name or None,
    )


def _get_notification_url(notification):
    if notification.link:
        if notification.link.startswith(("http://", "https://")):
            return notification.link
        return get_url(notification.link)
    if notification.document_type and notification.document_name:
        return get_url(f"/app/{frappe.scrub(notification.document_type)}/{notification.document_name}")
    return ""


def _outgoing_email_is_configured():
    return bool(
        frappe.db.exists(
            "Email Account",
            {"enable_outgoing": 1, "default_outgoing": 1},
        )
    )
