import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = [
        {"label": _("Advance"), "fieldname": "name", "fieldtype": "Link", "options": "Employee Advance", "width": 150},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
        {"label": _("Employee"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": _("Purpose"), "fieldname": "purpose", "fieldtype": "Data", "width": 240},
        {"label": _("Workflow"), "fieldname": "workflow_state", "fieldtype": "Data", "width": 120},
        {"label": _("Status"), "fieldname": "display_status", "fieldtype": "Data", "width": 125},
        {"label": _("Requested"), "fieldname": "advance_amount", "fieldtype": "Currency", "width": 115},
        {"label": _("Disbursed"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 115},
        {"label": _("Claimed"), "fieldname": "claimed_amount", "fieldtype": "Currency", "width": 115},
        {"label": _("Returned"), "fieldname": "return_amount", "fieldtype": "Currency", "width": 115},
        {"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 115},
        {"label": _("Due Date"), "fieldname": "custom_settlement_due_date", "fieldtype": "Date", "width": 100},
    ]
    conditions = ["ea.docstatus != 2"]
    values = {}
    roles = set(frappe.get_roles())
    privileged = bool(roles.intersection({"System Manager", "ESRM Approver", "HR Manager"})) or frappe.session.user == "Administrator"
    if not privileged and "ESRM Accounts" in roles:
        conditions.append("ea.docstatus = 1")
    elif not privileged and roles.intersection({"Employee", "ESRM Agent"}):
        employee = frappe.db.get_value(
            "Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
        )
        if not employee:
            return columns, []
        conditions.append("ea.employee = %(session_employee)s")
        values["session_employee"] = employee
    if filters.get("from_date"):
        conditions.append("ea.posting_date >= %(from_date)s")
        values["from_date"] = filters.from_date
    if filters.get("to_date"):
        conditions.append("ea.posting_date <= %(to_date)s")
        values["to_date"] = filters.to_date
    if filters.get("employee"):
        conditions.append("ea.employee = %(employee)s")
        values["employee"] = filters.employee

    rows = frappe.db.sql(
        f"""
        select ea.name, ea.posting_date, ea.employee, ea.employee_name, ea.purpose,
               ea.workflow_state, ea.status, ea.custom_cash_status, ea.advance_amount, ea.paid_amount,
               ea.claimed_amount, ea.return_amount, ea.custom_settlement_due_date
        from `tabEmployee Advance` ea
        where {' and '.join(conditions)}
        order by ea.posting_date desc, ea.name desc
        """,
        values,
        as_dict=True,
    )
    today = getdate(nowdate())
    data = []
    for row in rows:
        row.outstanding = max(flt(row.paid_amount) - flt(row.claimed_amount) - flt(row.return_amount), 0)
        overdue = bool(
            row.outstanding > 0 and row.custom_settlement_due_date
            and getdate(row.custom_settlement_due_date) < today
        )
        row.display_status = "Overdue" if overdue else (row.custom_cash_status or row.status)
        if filters.get("status") and filters.status not in {row.display_status, row.workflow_state}:
            continue
        data.append(row)
    return columns, data
