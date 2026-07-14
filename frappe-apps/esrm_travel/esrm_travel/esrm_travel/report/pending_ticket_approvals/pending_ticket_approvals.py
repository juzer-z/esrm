import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data)
    return columns, data, None, None, summary


def get_columns():
    return [
        {"label": _("Booking"), "fieldname": "name", "fieldtype": "Link", "options": "Ticket Booking", "width": 160},
        {"label": _("Approval"), "fieldname": "approval_status", "fieldtype": "Data", "width": 130},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 170},
        {"label": _("Passenger"), "fieldname": "passenger_name", "fieldtype": "Data", "width": 170},
        {"label": _("Airline"), "fieldname": "airline", "fieldtype": "Data", "width": 130},
        {"label": _("Issue Date"), "fieldname": "issue_date", "fieldtype": "Date", "width": 100},
        {"label": _("Flight Date"), "fieldname": "flight_date", "fieldtype": "Date", "width": 100},
        {"label": _("Agent"), "fieldname": "booking_owner", "fieldtype": "Link", "options": "User", "width": 150},
        {"label": _("Invoice Amount"), "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 130},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("approval_status"):
        conditions.append("tb.approval_status = %(approval_status)s")
        values["approval_status"] = filters.approval_status
    for fieldname in ["customer", "booking_owner", "airline"]:
        if filters.get(fieldname):
            conditions.append(f"tb.{fieldname} = %({fieldname})s")
            values[fieldname] = filters.get(fieldname)
    if filters.get("flight_from_date"):
        conditions.append("tb.flight_date >= %(flight_from_date)s")
        values["flight_from_date"] = filters.flight_from_date
    if filters.get("flight_to_date"):
        conditions.append("tb.flight_date <= %(flight_to_date)s")
        values["flight_to_date"] = filters.flight_to_date

    if "System Manager" not in frappe.get_roles():
        conditions.append("tb.booking_owner = %(current_user)s")
        values["current_user"] = frappe.session.user

    where_clause = " and ".join(conditions) if conditions else "1=1"
    return frappe.db.sql(
        f"""
        select
            tb.name,
            tb.approval_status,
            tb.customer,
            tb.passenger_name,
            tb.airline,
            tb.issue_date,
            tb.flight_date,
            tb.booking_owner,
            tb.invoice_amount,
            tb.status
        from `tabTicket Booking` tb
        where {where_clause}
        order by tb.flight_date asc, tb.modified desc
        """,
        values,
        as_dict=True,
    )


def get_summary(data):
    if not data:
        return []
    return [
        {"label": _("Pending Rows"), "value": len(data), "datatype": "Int", "indicator": "Orange"},
        {"label": _("Pending Value"), "value": sum(row.invoice_amount or 0 for row in data), "datatype": "Currency", "indicator": "Orange"},
    ]
