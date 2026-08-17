from html import escape

import frappe
from frappe.utils import cint, get_url, strip_html


EMAIL_CATEGORY_FIELDS = {
    "approval_required": "email_approval_required",
    "approval_decision": "email_approval_decisions",
    "assignment": "email_assignments",
    "booking_cost_update": "email_booking_cost_updates",
    "mention_comment": "email_mentions_comments",
    "general": "email_general_notifications",
}
RECOMMENDED_EMAIL_DEFAULTS = {
    "approval_required": 1,
    "approval_decision": 1,
    "assignment": 1,
    "booking_cost_update": 0,
    "mention_comment": 0,
    "general": 0,
}


def queue_notification_email(doc, method=None):
    """Queue configured email copies while preserving every in-app notification."""
    if not doc.for_user or doc.for_user == "Guest":
        return
    if not _email_is_enabled_for_notification(doc):
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


def _email_is_enabled_for_notification(notification):
    category = _get_notification_category(notification)
    fieldname = EMAIL_CATEGORY_FIELDS[category]
    configured_value = frappe.db.get_single_value("ESRM Travel Settings", fieldname)
    if configured_value is None:
        return bool(RECOMMENDED_EMAIL_DEFAULTS[category])
    return bool(cint(configured_value))


def _get_notification_category(notification):
    subject = strip_html(notification.subject or "").strip().lower()
    notification_type = (notification.type or "").strip().lower()

    if notification.document_type == "Ticket Booking":
        if subject.startswith("cost updated for ticket booking"):
            return "booking_cost_update"
        if subject.endswith("requires approval"):
            return "approval_required"
        if " was approved" in subject or " was rejected" in subject:
            return "approval_decision"

    if notification_type == "assignment" or "assigned you" in subject:
        return "assignment"
    if (
        notification_type in {"mention", "comment"}
        or "mentioned you" in subject
        or subject.startswith("new comment")
        or " commented on " in subject
    ):
        return "mention_comment"
    return "general"


def _outgoing_email_is_configured():
    return bool(
        frappe.db.exists(
            "Email Account",
            {"enable_outgoing": 1, "default_outgoing": 1},
        )
    )
