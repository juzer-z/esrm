import json
import os

import frappe


SITE_NAME = "development.localhost"
BENCH_SITES_PATH = "/workspace/frappe-dev/frappe-bench/sites"


def ensure_number_card(
    name,
    label,
    document_type,
    function,
    aggregate_field,
    filters=None,
    dynamic_filters=None,
):
    filters = filters or []
    dynamic_filters = dynamic_filters or []

    existing_name = frappe.db.get_value("Number Card", {"label": label, "module": "ESRM Travel"}, "name")

    if existing_name:
        doc = frappe.get_doc("Number Card", existing_name)
    else:
        doc = frappe.new_doc("Number Card")
        doc.label = label

    doc.module = "ESRM Travel"
    doc.label = label
    doc.type = "Document Type"
    doc.document_type = document_type
    doc.function = function
    doc.aggregate_function_based_on = aggregate_field
    doc.filters_json = json.dumps(filters)
    doc.dynamic_filters_json = json.dumps(dynamic_filters)
    doc.color = "Blue"
    doc.is_public = 1

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    return doc.name


def reset_child_table(parent_doc, table_fieldname):
    parent_doc.set(table_fieldname, [])


def add_shortcut(workspace, label, link_to, type_name="DocType", stats_filter=None):
    shortcut = workspace.append("shortcuts", {})
    shortcut.label = label
    shortcut.type = type_name
    shortcut.link_to = link_to
    shortcut.stats_filter = stats_filter
    return shortcut


def add_number_card(workspace, label, number_card_name):
    number_card = workspace.append("number_cards", {})
    number_card.label = label
    number_card.number_card_name = number_card_name
    return number_card


def add_link(
    workspace,
    label,
    link_to=None,
    type_name="Link",
    link_type="DocType",
    hidden=0,
    link_count=0,
):
    link = workspace.append("links", {})
    link.label = label
    link.type = type_name
    link.link_type = link_type
    link.link_to = link_to
    link.hidden = hidden
    link.link_count = link_count
    return link


def ensure_workspace(number_card_names):
    if frappe.db.exists("Workspace", "ESRM Travel"):
        workspace = frappe.get_doc("Workspace", "ESRM Travel")
    else:
        workspace = frappe.new_doc("Workspace")
        workspace.title = "ESRM Travel"
        workspace.name = "ESRM Travel"

    workspace.module = "ESRM Travel"
    workspace.label = "ESRM Travel"
    workspace.title = "ESRM Travel"
    workspace.public = 1
    workspace.is_hidden = 0
    workspace.content = json.dumps(
        [
            {"id": "hdr_dashboard", "type": "header", "data": {"text": "Travel Dashboard", "col": 12}},
            {"id": "nc_bookings", "type": "number_card", "data": {"number_card_name": number_card_names["bookings"], "col": 4}},
            {"id": "nc_invoiced", "type": "number_card", "data": {"number_card_name": number_card_names["invoiced"], "col": 4}},
            {"id": "nc_outstanding", "type": "number_card", "data": {"number_card_name": number_card_names["outstanding"], "col": 4}},
            {"id": "hdr_actions", "type": "header", "data": {"text": "Quick Actions", "col": 12}},
            {"id": "sc_ticket_booking", "type": "shortcut", "data": {"shortcut_name": "Ticket Booking", "col": 3}},
            {"id": "sc_customer", "type": "shortcut", "data": {"shortcut_name": "Customer", "col": 3}},
            {"id": "sc_sales_invoice", "type": "shortcut", "data": {"shortcut_name": "Sales Invoice", "col": 3}},
            {"id": "sc_payment_entry", "type": "shortcut", "data": {"shortcut_name": "Payment Entry", "col": 3}},
            {"id": "hdr_setup", "type": "header", "data": {"text": "Setup", "col": 12}},
            {"id": "sc_settings", "type": "shortcut", "data": {"shortcut_name": "ESRM Travel Settings", "col": 3}},
            {"id": "hdr_reports", "type": "header", "data": {"text": "Reports", "col": 12}},
            {"id": "sc_booking_register", "type": "shortcut", "data": {"shortcut_name": "Ticket Booking Register", "col": 4}},
            {"id": "sc_sales_collection", "type": "shortcut", "data": {"shortcut_name": "Ticket Sales and Collection Summary", "col": 4}},
            {"id": "sc_pending_approvals", "type": "shortcut", "data": {"shortcut_name": "Pending Ticket Approvals", "col": 4}},
            {"id": "card_operations", "type": "card", "data": {"card_name": "Operations", "col": 4}},
            {"id": "card_finance", "type": "card", "data": {"card_name": "Finance", "col": 4}},
            {"id": "card_setup", "type": "card", "data": {"card_name": "Setup", "col": 4}},
            {"id": "card_reports", "type": "card", "data": {"card_name": "Reports", "col": 4}},
        ]
    )

    reset_child_table(workspace, "number_cards")
    reset_child_table(workspace, "shortcuts")
    reset_child_table(workspace, "links")

    add_number_card(workspace, "Total Bookings", number_card_names["bookings"])
    add_number_card(workspace, "Invoiced Amount", number_card_names["invoiced"])
    add_number_card(workspace, "Outstanding Amount", number_card_names["outstanding"])

    add_shortcut(workspace, "Ticket Booking", "Ticket Booking")
    add_shortcut(workspace, "Customer", "Customer")
    add_shortcut(workspace, "Sales Invoice", "Sales Invoice")
    add_shortcut(workspace, "Payment Entry", "Payment Entry")
    add_shortcut(workspace, "ESRM Travel Settings", "ESRM Travel Settings")
    add_shortcut(workspace, "Ticket Booking Register", "Ticket Booking Register", type_name="Report")
    add_shortcut(
        workspace,
        "Ticket Sales and Collection Summary",
        "Ticket Sales and Collection Summary",
        type_name="Report",
    )
    add_shortcut(workspace, "Pending Ticket Approvals", "Pending Ticket Approvals", type_name="Report")

    add_link(workspace, "Operations", type_name="Card Break", link_count=2)
    add_link(workspace, "Ticket Booking", link_to="Ticket Booking")
    add_link(workspace, "Customer", link_to="Customer")

    add_link(workspace, "Finance", type_name="Card Break", link_count=2)
    add_link(workspace, "Sales Invoice", link_to="Sales Invoice")
    add_link(workspace, "Payment Entry", link_to="Payment Entry")

    add_link(workspace, "Setup", type_name="Card Break", link_count=1)
    add_link(workspace, "ESRM Travel Settings", link_to="ESRM Travel Settings")

    add_link(workspace, "Reports", type_name="Card Break", link_count=3)
    add_link(workspace, "Ticket Booking Register", link_to="Ticket Booking Register", link_type="Report")
    add_link(
        workspace,
        "Ticket Sales and Collection Summary",
        link_to="Ticket Sales and Collection Summary",
        link_type="Report",
    )
    add_link(workspace, "Pending Ticket Approvals", link_to="Pending Ticket Approvals", link_type="Report")

    if workspace.is_new():
        workspace.insert(ignore_permissions=True)
    else:
        workspace.save(ignore_permissions=True)


def hide_workspace(title):
    name = frappe.db.get_value("Workspace", {"title": title}, "name")
    if not name:
        return
    doc = frappe.get_doc("Workspace", name)
    doc.is_hidden = 1
    doc.save(ignore_permissions=True)


def update_module_profile():
    if not frappe.db.exists("Module Profile", "ESRM Lean Operations"):
        return

    profile = frappe.get_doc("Module Profile", "ESRM Lean Operations")
    blocked = {
        "Assets",
        "Bulk Transaction",
        "Buying",
        "Communication",
        "ERPNext Integrations",
        "Integrations",
        "Maintenance",
        "Manufacturing",
        "Portal",
        "Projects",
        "Quality Management",
        "Regional",
        "Stock",
        "Subcontracting",
        "Support",
        "Telephony",
        "Website",
    }

    current = {row.module for row in profile.get("block_modules", [])}
    for module_name in sorted(blocked - current):
        row = profile.append("block_modules", {})
        row.module = module_name

    profile.save(ignore_permissions=True)


def print_status():
    workspace = frappe.get_doc("Workspace", "ESRM Travel")
    print("Workspace content blocks:", len(json.loads(workspace.content or "[]")))
    print(
        "Workspace shortcuts:",
        [row.label for row in workspace.shortcuts],
    )
    print(
        "Visible workspaces:",
        frappe.get_all(
            "Workspace",
            filters={"public": 1, "is_hidden": 0},
            pluck="title",
            order_by="title asc",
        ),
    )


def main():
    os.chdir(BENCH_SITES_PATH)
    frappe.init(site=SITE_NAME)
    frappe.connect()

    number_card_names = {}

    number_card_names["bookings"] = ensure_number_card(
        name="ESRM Total Bookings",
        label="Total Bookings",
        document_type="Ticket Booking",
        function="Count",
        aggregate_field="name",
        filters=[["Ticket Booking", "docstatus", "!=", "2", False]],
    )
    number_card_names["invoiced"] = ensure_number_card(
        name="ESRM Invoiced Amount",
        label="Invoiced Amount",
        document_type="Sales Invoice",
        function="Sum",
        aggregate_field="grand_total",
        filters=[
            ["Sales Invoice", "docstatus", "!=", "2", False],
            ["Sales Invoice", "esrm_ticket_booking", "is", "set", False],
        ],
    )
    number_card_names["outstanding"] = ensure_number_card(
        name="ESRM Outstanding Amount",
        label="Outstanding Amount",
        document_type="Sales Invoice",
        function="Sum",
        aggregate_field="outstanding_amount",
        filters=[
            ["Sales Invoice", "docstatus", "!=", "2", False],
            ["Sales Invoice", "esrm_ticket_booking", "is", "set", False],
        ],
    )

    ensure_workspace(number_card_names)
    hide_workspace("Buying")
    update_module_profile()

    frappe.clear_cache()
    frappe.db.commit()
    print_status()
    frappe.destroy()


if __name__ == "__main__":
    main()
