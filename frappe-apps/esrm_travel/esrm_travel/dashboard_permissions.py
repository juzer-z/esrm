import frappe


ADMIN_ONLY_NUMBER_CARDS = {"Profit"}
ADMIN_ONLY_CHARTS = {"ESRM Profit by Reference"}


def number_card_has_permission(doc, user=None, permission_type=None):
    if doc.name in ADMIN_ONLY_NUMBER_CARDS and (user or frappe.session.user) != "Administrator":
        return False
    return None


def dashboard_chart_has_permission(doc, user=None, permission_type=None):
    if doc.name in ADMIN_ONLY_CHARTS and (user or frappe.session.user) != "Administrator":
        return False
    return None
