import json

import frappe
from esrm_travel.access_control import setup_access_controls
from esrm_travel.branding import apply_branding
from esrm_travel.chart_of_accounts import get_company, setup_chart_of_accounts
from esrm_travel.print_formats import setup_print_formats


def setup_workspace():
    setup_access_controls()
    apply_branding()
    setup_chart_of_accounts()
    setup_print_formats()
    ensure_fiscal_years()
    ensure_accounting_defaults()
    recalculate_ticket_profitability()
    setup_number_cards()
    setup_charts()
    setup_esrm_workspace()
    hide_old_esrm_travel_workspace()


def ensure_fiscal_years():
    company = get_company()
    if not company:
        return

    for year, start_date, end_date in get_required_fiscal_years():
        if frappe.db.exists("Fiscal Year", year):
            fiscal_year = frappe.get_doc("Fiscal Year", year)
        else:
            fiscal_year = frappe.get_doc({"doctype": "Fiscal Year", "year": year})

        fiscal_year.year_start_date = start_date
        fiscal_year.year_end_date = end_date
        fiscal_year.disabled = 0

        valid_company_rows = [
            row for row in fiscal_year.get("companies", []) if frappe.db.exists("Company", row.company)
        ]
        fiscal_year.set("companies", valid_company_rows)

        linked_companies = {row.company for row in fiscal_year.get("companies", [])}
        if company not in linked_companies:
            fiscal_year.append("companies", {"company": company})

        save_doc(fiscal_year)

    frappe.cache().hdel("fiscal_years", company)


def get_required_fiscal_years():
    return [
        ("2025-2026", "2025-07-01", "2026-06-30"),
        ("2026-2027", "2026-07-01", "2027-06-30"),
        ("2027-2028", "2027-07-01", "2028-06-30"),
    ]

def ensure_accounting_defaults():
    company = get_company()
    if not company:
        return

    root_cost_center = f"{company} - ESRM"
    default_cost_center = "Main - ESRM"
    default_income_account = "Air Ticket Sales-International - ESRM"

    if not frappe.db.exists("Company", company):
        return

    if not frappe.db.exists("Cost Center", default_cost_center):
        cost_center = frappe.get_doc(
            {
                "doctype": "Cost Center",
                "cost_center_name": "Main",
                "company": company,
                "parent_cost_center": root_cost_center if frappe.db.exists("Cost Center", root_cost_center) else None,
                "is_group": 0,
                "disabled": 0,
            }
        )
        cost_center.insert(ignore_permissions=True)

    if not frappe.db.exists("DocType", "ESRM Travel Settings"):
        return

    settings = frappe.get_single("ESRM Travel Settings")
    current = settings.default_cost_center
    current_is_group = bool(current and frappe.db.get_value("Cost Center", current, "is_group"))

    if not current or current_is_group:
        settings.default_cost_center = default_cost_center

    if not settings.default_company:
        settings.default_company = company

    income_account_root_type = None
    income_account_is_group = 0
    if settings.default_income_account:
        income_account_root_type, income_account_is_group = frappe.db.get_value(
            "Account",
            settings.default_income_account,
            ["root_type", "is_group"],
        ) or (None, 0)

    if (
        frappe.db.exists("Account", default_income_account)
        and (
            not settings.default_income_account
            or income_account_root_type != "Income"
            or income_account_is_group
        )
    ):
        settings.default_income_account = default_income_account

    if (
        settings.has_value_changed("default_company")
        or settings.has_value_changed("default_cost_center")
        or settings.has_value_changed("default_income_account")
    ):
        settings.flags.ignore_mandatory = True
        settings.save(ignore_permissions=True)

    frappe.db.sql(
        """
        update `tabSales Invoice Item` item
        inner join `tabSales Invoice` invoice on invoice.name = item.parent
        set item.cost_center = %(default_cost_center)s
        where invoice.docstatus = 0
          and invoice.esrm_ticket_booking is not null
          and invoice.esrm_ticket_booking != ''
          and item.cost_center = %(root_cost_center)s
        """,
        {
            "default_cost_center": default_cost_center,
            "root_cost_center": root_cost_center,
        },
    )


def recalculate_ticket_profitability():
    if not frappe.db.exists("DocType", "Ticket Booking"):
        return

    frappe.db.sql(
        """
        update `tabTicket Booking`
        set
            commission = case
                when payment_mode = 'IATA'
                then ifnull(gross_amount, 0) - ifnull(iata_amount, 0)
                else 0
            end,
            discount = ifnull(gross_amount, 0) - ifnull(invoice_amount, 0),
            profit = case
                when payment_mode = 'IATA'
                then ifnull(invoice_amount, 0) - ifnull(iata_amount, 0)
                else ifnull(invoice_amount, 0) - ifnull(supplier_cost, 0)
            end
        where docstatus != 2
        """
    )


def setup_number_cards():
    cards = [
        {
            "name": "Total Bookings",
            "label": "Total Bookings",
            "document_type": "Ticket Booking",
            "function": "Count",
            "aggregate_function_based_on": "name",
            "filters_json": [["Ticket Booking", "docstatus", "!=", "2", False]],
            "color": "Blue",
        },
        {
            "name": "Pending Approvals",
            "label": "Pending Approvals",
            "document_type": "Ticket Booking",
            "function": "Count",
            "aggregate_function_based_on": "name",
            "filters_json": [["Ticket Booking", "approval_status", "=", "Pending Approval", False]],
            "color": "Orange",
        },
        {
            "name": "Issued Today",
            "label": "Issued Today",
            "document_type": "Ticket Booking",
            "function": "Count",
            "aggregate_function_based_on": "name",
            "filters_json": [["Ticket Booking", "docstatus", "!=", "2", False]],
            "dynamic_filters_json": [["Ticket Booking", "issue_date", "=", "frappe.datetime.nowdate()"]],
            "color": "Green",
        },
        {
            "name": "Profit",
            "label": "Profit",
            "document_type": "Ticket Booking",
            "function": "Sum",
            "aggregate_function_based_on": "profit",
            "filters_json": [["Ticket Booking", "docstatus", "!=", "2", False]],
            "color": "Green",
        },
        {
            "name": "Outstanding Amount",
            "label": "Outstanding Amount",
            "document_type": "Ticket Booking",
            "function": "Sum",
            "aggregate_function_based_on": "outstanding_amount",
            "filters_json": [["Ticket Booking", "docstatus", "!=", "2", False]],
            "color": "Red",
        },
    ]

    for card in cards:
        upsert_number_card(card)


def upsert_number_card(card):
    doc = get_or_create("Number Card", card["name"])
    doc.update(
        {
            "label": card["label"],
            "module": "ESRM Travel",
            "type": "Document Type",
            "document_type": card["document_type"],
            "function": card["function"],
            "aggregate_function_based_on": card["aggregate_function_based_on"],
            "is_public": 1,
            "show_full_number": 1,
            "show_percentage_stats": 0,
            "stats_time_interval": "Daily",
            "filters_json": json.dumps(card.get("filters_json", [])),
            "dynamic_filters_json": json.dumps(card.get("dynamic_filters_json", [])),
            "color": card["color"],
        }
    )
    save_doc(doc)


def setup_charts():
    charts = [
        {
            "name": "ESRM Booking Pipeline",
            "chart_name": "ESRM Booking Pipeline",
            "document_type": "Ticket Booking",
            "type": "Donut",
            "group_by_type": "Count",
            "group_by_based_on": "status",
            "custom_options": {"truncateLegends": 1, "maxSlices": 8},
        },
        {
            "name": "ESRM Profit by Reference",
            "chart_name": "ESRM Profit by Reference",
            "document_type": "Ticket Booking",
            "type": "Bar",
            "group_by_type": "Sum",
            "group_by_based_on": "reference",
            "aggregate_function_based_on": "profit",
            "number_of_groups": 10,
            "custom_options": {"truncateLegends": 1},
        },
    ]

    for chart in charts:
        upsert_chart(chart)


def upsert_chart(chart):
    doc = get_or_create("Dashboard Chart", chart["name"])
    doc.update(
        {
            "chart_name": chart["chart_name"],
            "module": "ESRM Travel",
            "chart_type": "Group By",
            "document_type": chart["document_type"],
            "type": chart["type"],
            "group_by_type": chart["group_by_type"],
            "group_by_based_on": chart["group_by_based_on"],
            "aggregate_function_based_on": chart.get("aggregate_function_based_on"),
            "number_of_groups": chart.get("number_of_groups", 0),
            "is_public": 1,
            "is_standard": 0,
            "filters_json": json.dumps([["Ticket Booking", "docstatus", "!=", "2", False]]),
            "dynamic_filters_json": json.dumps([]),
            "custom_options": json.dumps(chart.get("custom_options", {})),
        }
    )
    save_doc(doc)


def setup_esrm_workspace():
    workspace = get_or_create("Workspace", "ESRM")
    workspace.update(
        {
            "label": "ESRM",
            "title": "ESRM",
            "module": "ESRM Travel",
            "icon": "plane",
            "indicator_color": "blue",
            "public": 1,
            "is_hidden": 0,
            "hide_custom": 0,
            "content": json.dumps(get_workspace_content()),
        }
    )

    workspace.set("number_cards", [{"number_card_name": card, "label": label} for card, label in NUMBER_CARDS])
    workspace.set("charts", [{"chart_name": chart, "label": label} for chart, label in CHARTS])
    workspace.set("shortcuts", SHORTCUTS)
    workspace.set("links", LINKS)

    save_doc(workspace)


def hide_old_esrm_travel_workspace():
    if not frappe.db.exists("Workspace", "ESRM Travel"):
        return

    workspace = frappe.get_doc("Workspace", "ESRM Travel")
    workspace.is_hidden = 1
    save_doc(workspace)


NUMBER_CARDS = [
    ("Total Bookings", "Total Bookings"),
    ("Pending Approvals", "Pending Approvals"),
    ("Issued Today", "Issued Today"),
    ("Profit", "Profit"),
    ("Outstanding Amount", "Outstanding Amount"),
]

CHARTS = [
    ("ESRM Booking Pipeline", "Booking Pipeline"),
    ("ESRM Profit by Reference", "Profit by Reference"),
]

SHORTCUTS = [
    {"type": "DocType", "link_to": "Ticket Booking", "doc_view": "New", "label": "New Booking", "color": "#0b7285"},
    {"type": "DocType", "link_to": "Ticket Booking", "doc_view": "List", "label": "Find Booking", "color": "#364fc7"},
    {"type": "Report", "link_to": "Pending Ticket Approvals", "label": "Pending Approvals", "color": "#f08c00"},
    {"type": "Report", "link_to": "Ticket Booking Register", "label": "Search Register", "color": "#2f9e44"},
    {"type": "DocType", "link_to": "Customer", "doc_view": "List", "label": "Customers", "color": "#495057"},
    {"type": "DocType", "link_to": "Sales Invoice", "doc_view": "List", "label": "Invoices", "color": "#1971c2"},
    {"type": "DocType", "link_to": "Payment Entry", "doc_view": "List", "label": "Collections", "color": "#2b8a3e"},
    {"type": "Report", "link_to": "Ticket Sales and Collection Summary", "label": "Sales Summary", "color": "#862e9c"},
]

LINKS = [
    {"type": "Card Break", "label": "Daily Operations", "icon": "calendar", "description": "Create tickets, track references, update IATA amounts, and find bookings quickly."},
    {"type": "Link", "label": "Ticket Booking", "link_type": "DocType", "link_to": "Ticket Booking"},
    {"type": "Link", "label": "Customer", "link_type": "DocType", "link_to": "Customer"},
    {"type": "Link", "label": "Ticket Sector", "link_type": "DocType", "link_to": "Ticket Sector"},
    {"type": "Card Break", "label": "Billing & Collection", "icon": "accounting", "description": "Create invoices from approved tickets and follow up on outstanding balances."},
    {"type": "Link", "label": "Sales Invoice", "link_type": "DocType", "link_to": "Sales Invoice"},
    {"type": "Link", "label": "Payment Entry", "link_type": "DocType", "link_to": "Payment Entry"},
    {"type": "Card Break", "label": "Reports", "icon": "chart", "description": "Use these views for monthly statements, payment follow-up, and profitability checks."},
    {"type": "Link", "label": "Ticket Booking Register", "link_type": "Report", "link_to": "Ticket Booking Register", "is_query_report": 1, "report_ref_doctype": "Ticket Booking"},
    {"type": "Link", "label": "Ticket Sales and Collection Summary", "link_type": "Report", "link_to": "Ticket Sales and Collection Summary", "is_query_report": 1, "report_ref_doctype": "Ticket Booking"},
    {"type": "Link", "label": "Pending Ticket Approvals", "link_type": "Report", "link_to": "Pending Ticket Approvals", "is_query_report": 1, "report_ref_doctype": "Ticket Booking"},
    {"type": "Card Break", "label": "Setup", "icon": "setting", "description": "Configure defaults before billing or using finance flows."},
    {"type": "Link", "label": "ESRM Settings", "link_type": "DocType", "link_to": "ESRM Travel Settings"},
]


def get_workspace_content():
    return [
        header("Today at a Glance"),
        number_card("Total Bookings", 2),
        number_card("Pending Approvals", 2),
        number_card("Issued Today", 2),
        number_card("Profit", 3),
        number_card("Outstanding Amount", 3),
        spacer(),
        header("Quick Workflows"),
        shortcut("New Booking", 3),
        shortcut("Find Booking", 3),
        shortcut("Pending Approvals", 3),
        shortcut("Search Register", 3),
        shortcut("Customers", 3),
        shortcut("Invoices", 3),
        shortcut("Collections", 3),
        shortcut("Sales Summary", 3),
        spacer(),
        header("Operational Signals"),
        chart("ESRM Booking Pipeline", 6),
        chart("ESRM Profit by Reference", 6),
        spacer(),
        header("Work Areas"),
        card("Daily Operations", 4),
        card("Billing & Collection", 4),
        card("Reports", 4),
        card("Setup", 4),
    ]


def header(text):
    return {"id": frappe.generate_hash(length=10), "type": "header", "data": {"text": f'<span class="h4"><b>{text}</b></span>', "col": 12}}


def spacer():
    return {"id": frappe.generate_hash(length=10), "type": "spacer", "data": {"col": 12}}


def number_card(name, col):
    return {"id": frappe.generate_hash(length=10), "type": "number_card", "data": {"number_card_name": name, "col": col}}


def shortcut(name, col):
    return {"id": frappe.generate_hash(length=10), "type": "shortcut", "data": {"shortcut_name": name, "col": col}}


def chart(name, col):
    return {"id": frappe.generate_hash(length=10), "type": "chart", "data": {"chart_name": name, "col": col}}


def card(name, col):
    return {"id": frappe.generate_hash(length=10), "type": "card", "data": {"card_name": name, "col": col}}


def get_or_create(doctype, name):
    if frappe.db.exists(doctype, name):
        return frappe.get_doc(doctype, name)
    return frappe.new_doc(doctype).update({"doctype": doctype, "name": name})


def save_doc(doc):
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
