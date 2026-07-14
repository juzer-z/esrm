import frappe
from frappe import _


GROUP_FIELD_MAP = {
    "Customer": ("customer", "Customer", "Link", "Customer"),
    "Reference": ("reference", "Reference", "Data", None),
    "Booking Owner": ("booking_owner", "Booking Owner", "Link", "User"),
    "Airline": ("airline", "Airline", "Data", None),
    "Payment Mode": ("payment_mode", "Payment Mode", "Data", None),
}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart(data, filters)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns(filters):
    fieldname, label, fieldtype, options = GROUP_FIELD_MAP.get(filters.get("based_on") or "Customer")
    columns = [
        {"label": _(label), "fieldname": "group_by", "fieldtype": fieldtype, "width": 180},
    ]
    if options:
        columns[0]["options"] = options

    columns.extend(
        [
            {"label": _("Bookings"), "fieldname": "bookings", "fieldtype": "Int", "width": 90},
            {"label": _("Approved"), "fieldname": "approved_bookings", "fieldtype": "Int", "width": 90},
            {"label": _("Pending"), "fieldname": "pending_bookings", "fieldtype": "Int", "width": 90},
            {"label": _("Invoice Amount"), "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 140},
            {"label": _("Gross Amount"), "fieldname": "gross_amount", "fieldtype": "Currency", "width": 130},
            {"label": _("IATA Amount"), "fieldname": "iata_amount", "fieldtype": "Currency", "width": 130},
            {"label": _("Commission"), "fieldname": "commission", "fieldtype": "Currency", "width": 120},
            {"label": _("Discount"), "fieldname": "discount", "fieldtype": "Currency", "width": 120},
            {"label": _("Profit"), "fieldname": "profit", "fieldtype": "Currency", "width": 120},
            {"label": _("Collected"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 130},
            {"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 130},
        ]
    )
    return columns


def get_conditions(filters):
    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("tb.issue_date >= %(from_date)s")
        values["from_date"] = filters.from_date
    if filters.get("to_date"):
        conditions.append("tb.issue_date <= %(to_date)s")
        values["to_date"] = filters.to_date

    for fieldname in ["approval_status", "status", "customer", "reference", "booking_owner"]:
        if filters.get(fieldname):
            conditions.append(f"tb.{fieldname} = %({fieldname})s")
            values[fieldname] = filters.get(fieldname)

    if "System Manager" not in frappe.get_roles():
        conditions.append("tb.booking_owner = %(current_user)s")
        values["current_user"] = frappe.session.user

    return (" and ".join(conditions) if conditions else "1=1"), values


def get_data(filters):
    group_field = GROUP_FIELD_MAP.get(filters.get("based_on") or "Customer")[0]
    where_clause, values = get_conditions(filters)

    return frappe.db.sql(
        f"""
        select
            coalesce(tb.{group_field}, 'Not Specified') as group_by,
            count(tb.name) as bookings,
            sum(case when tb.approval_status = 'Approved' then 1 else 0 end) as approved_bookings,
            sum(case when tb.approval_status = 'Pending Approval' then 1 else 0 end) as pending_bookings,
            sum(coalesce(tb.invoice_amount, 0)) as invoice_amount,
            sum(coalesce(tb.gross_amount, 0)) as gross_amount,
            sum(coalesce(tb.iata_amount, 0)) as iata_amount,
            sum(coalesce(tb.commission, 0)) as commission,
            sum(coalesce(tb.discount, 0)) as discount,
            sum(coalesce(tb.profit, 0)) as profit,
            sum(coalesce(tb.paid_amount, 0)) as paid_amount,
            sum(coalesce(tb.outstanding_amount, 0)) as outstanding_amount
        from `tabTicket Booking` tb
        where {where_clause}
        group by tb.{group_field}
        order by invoice_amount desc, bookings desc
        """,
        values,
        as_dict=True,
    )


def get_chart(data, filters):
    if not data:
        return None

    top_rows = data[:8]
    return {
        "data": {
            "labels": [row.group_by for row in top_rows],
            "datasets": [
                {"name": _("Invoice Amount"), "values": [row.invoice_amount for row in top_rows]},
                {"name": _("Profit"), "values": [row.profit for row in top_rows]},
                {"name": _("Collected"), "values": [row.paid_amount for row in top_rows]},
            ],
        },
        "type": "bar",
    }


def get_summary(data):
    if not data:
        return []

    return [
        {"label": _("Groups"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
        {"label": _("Invoice Amount"), "value": sum(row.invoice_amount or 0 for row in data), "datatype": "Currency", "indicator": "Green"},
        {"label": _("Profit"), "value": sum(row.profit or 0 for row in data), "datatype": "Currency", "indicator": "Green"},
        {"label": _("Collected"), "value": sum(row.paid_amount or 0 for row in data), "datatype": "Currency", "indicator": "Green"},
        {"label": _("Outstanding"), "value": sum(row.outstanding_amount or 0 for row in data), "datatype": "Currency", "indicator": "Orange"},
    ]
