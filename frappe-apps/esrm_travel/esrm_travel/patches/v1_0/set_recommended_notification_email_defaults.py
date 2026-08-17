import frappe


def execute():
    settings = frappe.get_single("ESRM Travel Settings")
    settings.update(
        {
            "email_approval_required": 1,
            "email_approval_decisions": 1,
            "email_assignments": 1,
            "email_booking_cost_updates": 0,
            "email_mentions_comments": 0,
            "email_general_notifications": 0,
        }
    )
    settings.save(ignore_permissions=True)
