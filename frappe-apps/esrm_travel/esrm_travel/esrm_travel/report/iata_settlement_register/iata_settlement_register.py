import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    conditions = []
    values = {}
    if filters.get("from_date"):
        conditions.append("settlement.deposit_date >= %(from_date)s")
        values["from_date"] = getdate(filters.from_date)
    if filters.get("to_date"):
        conditions.append("settlement.deposit_date <= %(to_date)s")
        values["to_date"] = getdate(filters.to_date)
    if filters.get("status"):
        conditions.append("settlement.status = %(status)s")
        values["status"] = filters.status
    if filters.get("source_account"):
        conditions.append("settlement.source_account = %(source_account)s")
        values["source_account"] = filters.source_account
    where = " and " + " and ".join(conditions) if conditions else ""
    data = frappe.db.sql(
        f"""
        select settlement.name, settlement.period_from, settlement.period_to,
               settlement.deposit_date, settlement.reference_no,
               settlement.source_account, settlement.international_amount,
               settlement.domestic_amount, settlement.expected_total,
               settlement.deposit_amount, settlement.difference_amount,
               settlement.status, settlement.journal_entry,
               ifnull(booking.booking_count, 0) as booking_count
        from `tabIATA Settlement` settlement
        left join (
            select parent, count(name) as booking_count
            from `tabIATA Settlement Booking`
            where parenttype = 'IATA Settlement'
            group by parent
        ) booking on booking.parent = settlement.name
        where 1=1 {where}
        order by settlement.deposit_date desc, settlement.name desc
        """,
        values,
        as_dict=True,
    )
    columns = [
        {"label": _("Settlement"), "fieldname": "name", "fieldtype": "Link", "options": "IATA Settlement", "width": 150},
        {"label": _("Period From"), "fieldname": "period_from", "fieldtype": "Date", "width": 100},
        {"label": _("Period To"), "fieldname": "period_to", "fieldtype": "Date", "width": 100},
        {"label": _("Deposit Date"), "fieldname": "deposit_date", "fieldtype": "Date", "width": 105},
        {"label": _("Reference"), "fieldname": "reference_no", "fieldtype": "Data", "width": 130},
        {"label": _("Bookings"), "fieldname": "booking_count", "fieldtype": "Int", "width": 80},
        {"label": _("International"), "fieldname": "international_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Domestic"), "fieldname": "domestic_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("Expected"), "fieldname": "expected_total", "fieldtype": "Currency", "width": 120},
        {"label": _("Deposited"), "fieldname": "deposit_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Difference"), "fieldname": "difference_amount", "fieldtype": "Currency", "width": 105},
        {"label": _("Paid From"), "fieldname": "source_account", "fieldtype": "Link", "options": "Account", "width": 170},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
        {"label": _("Journal Entry"), "fieldname": "journal_entry", "fieldtype": "Link", "options": "Journal Entry", "width": 150},
    ]
    summary = [
        {"label": _("Settlements"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
        {"label": _("Bookings"), "value": sum(row.booking_count or 0 for row in data), "datatype": "Int", "indicator": "Blue"},
        {"label": _("Cash Deposited"), "value": sum(row.deposit_amount or 0 for row in data if row.status == "Submitted"), "datatype": "Currency", "indicator": "Green"},
    ]
    return columns, data, None, None, summary
