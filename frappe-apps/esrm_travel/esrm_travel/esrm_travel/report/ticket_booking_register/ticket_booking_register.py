import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": _("Booking"), "fieldname": "name", "fieldtype": "Link", "options": "Ticket Booking", "width": 160},
        {"label": _("Issue Date"), "fieldname": "issue_date", "fieldtype": "Date", "width": 100},
        {"label": _("Flight Date"), "fieldname": "flight_date", "fieldtype": "Date", "width": 100},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 170},
        {"label": _("Passenger"), "fieldname": "passenger_name", "fieldtype": "Data", "width": 160},
        {"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 120},
        {"label": _("Airline"), "fieldname": "airline", "fieldtype": "Data", "width": 130},
        {"label": _("Ticket Number"), "fieldname": "ticket_number", "fieldtype": "Data", "width": 150},
        {"label": _("Invoice Number"), "fieldname": "invoice_number", "fieldtype": "Data", "width": 130},
        {"label": _("Route"), "fieldname": "route_summary", "fieldtype": "Data", "width": 150},
        {"label": _("Agent"), "fieldname": "booking_owner", "fieldtype": "Link", "options": "User", "width": 150},
        {"label": _("Approval"), "fieldname": "approval_status", "fieldtype": "Data", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("Invoice Status"), "fieldname": "invoice_status", "fieldtype": "Data", "width": 120},
        {"label": _("Payment Mode"), "fieldname": "payment_mode", "fieldtype": "Data", "width": 110},
        {"label": _("Gross Amount"), "fieldname": "gross_amount", "fieldtype": "Currency", "width": 130},
        {"label": _("IATA Amount"), "fieldname": "iata_amount", "fieldtype": "Currency", "width": 130},
        {"label": _("Invoice Amount"), "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 130},
        {"label": _("Commission"), "fieldname": "commission", "fieldtype": "Currency", "width": 120},
        {"label": _("Discount"), "fieldname": "discount", "fieldtype": "Currency", "width": 120},
        {"label": _("Profit"), "fieldname": "profit", "fieldtype": "Currency", "width": 120},
        {"label": _("Paid Amount"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 130},
        {"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 130},
        {"label": _("Sales Invoice"), "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("tb.issue_date >= %(from_date)s")
        values["from_date"] = filters.from_date
    if filters.get("to_date"):
        conditions.append("tb.issue_date <= %(to_date)s")
        values["to_date"] = filters.to_date
    if filters.get("flight_from_date"):
        conditions.append("tb.flight_date >= %(flight_from_date)s")
        values["flight_from_date"] = filters.flight_from_date
    if filters.get("flight_to_date"):
        conditions.append("tb.flight_date <= %(flight_to_date)s")
        values["flight_to_date"] = filters.flight_to_date

    for fieldname in ["customer", "reference", "airline", "booking_owner", "approval_status", "status", "invoice_status", "payment_mode"]:
        if filters.get(fieldname):
            conditions.append(f"tb.{fieldname} = %({fieldname})s")
            values[fieldname] = filters.get(fieldname)

    if filters.get("search"):
        conditions.append(
            """
            (
                tb.ticket_number like %(search)s
                or tb.invoice_number like %(search)s
                or tb.customer like %(search)s
                or tb.passenger_name like %(search)s
                or tb.reference like %(search)s
            )
            """
        )
        values["search"] = f"%{filters.search}%"

    if "System Manager" not in frappe.get_roles():
        conditions.append("tb.booking_owner = %(current_user)s")
        values["current_user"] = frappe.session.user

    where_clause = " and ".join(conditions) if conditions else "1=1"
    return frappe.db.sql(
        f"""
        select
            tb.name,
            tb.issue_date,
            tb.flight_date,
            tb.customer,
            tb.passenger_name,
            tb.reference,
            tb.airline,
            tb.ticket_number,
            tb.invoice_number,
            tb.route_summary,
            tb.booking_owner,
            tb.approval_status,
            tb.status,
            tb.invoice_status,
            tb.payment_mode,
            tb.gross_amount,
            tb.iata_amount,
            tb.invoice_amount,
            tb.commission,
            tb.discount,
            tb.profit,
            tb.paid_amount,
            tb.outstanding_amount,
            tb.sales_invoice
        from `tabTicket Booking` tb
        where {where_clause}
        order by tb.issue_date desc, tb.modified desc
        """,
        values,
        as_dict=True,
    )


def get_chart(data):
    if not data:
        return None

    counts = {}
    for row in data:
        counts[row.approval_status] = counts.get(row.approval_status, 0) + 1

    return {
        "data": {
            "labels": list(counts.keys()),
            "datasets": [{"name": _("Bookings"), "values": list(counts.values())}],
        },
        "type": "donut",
    }


def get_summary(data):
    if not data:
        return []

    total_invoice = sum(row.invoice_amount or 0 for row in data)
    total_paid = sum(row.paid_amount or 0 for row in data)
    total_outstanding = sum(row.outstanding_amount or 0 for row in data)

    return [
        {"label": _("Bookings"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
        {"label": _("Invoice Amount"), "value": total_invoice, "datatype": "Currency", "indicator": "Green"},
        {"label": _("Collected"), "value": total_paid, "datatype": "Currency", "indicator": "Green"},
        {"label": _("Outstanding"), "value": total_outstanding, "datatype": "Currency", "indicator": "Orange"},
    ]
