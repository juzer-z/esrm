import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate


PRIVILEGED_ROLES = {"System Manager", "ESRM Approver", "ESRM Accounts", "HR Manager"}
EMPLOYEE_ROLES = {"Employee", "ESRM Agent"}
ADVANCE_ACCOUNT = "Staff Cash Advances - ESRM"


def _roles(user=None):
    return set(frappe.get_roles(user or frappe.session.user))


def _is_privileged(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or bool(_roles(user) & PRIVILEGED_ROLES)


def _employee_for_user(user=None):
    return frappe.db.get_value(
        "Employee", {"user_id": user or frappe.session.user, "status": "Active"}, "name"
    )


def before_validate_employee_advance(doc, method=None):
    if not _is_privileged() and _roles() & EMPLOYEE_ROLES:
        employee = _employee_for_user()
        if not employee:
            frappe.throw(_("Your user account must be linked to an active Employee before requesting cash."))
        if doc.employee and doc.employee != employee:
            frappe.throw(_("You can only request a cash advance for yourself."))
        doc.employee = employee

    if doc.employee and not doc.company:
        doc.company = frappe.db.get_value("Employee", doc.employee, "company")
    doc.advance_account = ADVANCE_ACCOUNT
    doc.currency = doc.currency or frappe.db.get_value("Company", doc.company, "default_currency") or "BDT"
    doc.exchange_rate = doc.exchange_rate or 1
    if doc.posting_date and flt(doc.paid_amount) > 0 and not doc.custom_settlement_due_date:
        doc.custom_settlement_due_date = add_days(doc.posting_date, 7)
    if doc.docstatus == 0:
        doc.custom_cash_status = doc.workflow_state or "Draft"


def on_submit_employee_advance(doc, method=None):
    update_cash_advance_status(doc.name)


def on_cancel_employee_advance(doc, method=None):
    update_cash_advance_status(doc.name)


def before_validate_expense_claim(doc, method=None):
    if not _is_privileged() and _roles() & EMPLOYEE_ROLES:
        employee = _employee_for_user()
        if not employee:
            frappe.throw(_("Your user account must be linked to an active Employee before submitting expenses."))
        if doc.employee and doc.employee != employee:
            frappe.throw(_("You can only submit expenses for yourself."))
        doc.employee = employee

    for row in doc.expenses:
        if not _is_privileged() and not flt(row.sanctioned_amount):
            row.sanctioned_amount = row.amount

    linked = [row for row in doc.advances if row.employee_advance]
    if not linked:
        return
    if len(linked) != 1:
        frappe.throw(_("A cash settlement must relate to exactly one Employee Advance."))

    advance = frappe.db.get_value(
        "Employee Advance", linked[0].employee_advance,
        ["employee", "docstatus", "paid_amount", "claimed_amount", "return_amount"], as_dict=True,
    )
    if not advance or advance.docstatus != 1:
        frappe.throw(_("The linked Employee Advance must be approved before it can be settled."))
    if advance.employee != doc.employee:
        frappe.throw(_("The linked Employee Advance belongs to a different employee."))
    available = max(flt(advance.paid_amount) - flt(advance.claimed_amount) - flt(advance.return_amount), 0)
    sanctioned = sum(flt(row.sanctioned_amount) for row in doc.expenses)
    linked[0].allocated_amount = min(sanctioned, available)
    doc.custom_cash_advance = linked[0].employee_advance
    doc.custom_settlement_variance = sanctioned - available


def before_submit_expense_claim(doc, method=None):
    if not doc.custom_cash_advance:
        return
    if not any(row.custom_receipt_attachment for row in doc.expenses):
        frappe.throw(_("Attach at least one receipt or supporting document before submitting the settlement."))

    if flt(doc.custom_settlement_variance) > 0 and not _is_privileged():
        frappe.throw(_("Expenses exceed the available advance. Send this settlement to Accounts for review."))
    doc.approval_status = "Approved"


def _employee_condition(user=None):
    user = user or frappe.session.user
    employee = _employee_for_user(user)
    escaped_user = frappe.db.escape(user)
    if employee:
        return f"(`tab{{doctype}}`.employee = {frappe.db.escape(employee)} or `tab{{doctype}}`.owner = {escaped_user})"
    return f"`tab{{doctype}}`.owner = {escaped_user}"


def employee_advance_query_conditions(user=None):
    user = user or frappe.session.user
    roles = _roles(user)
    if user != "Administrator" and "ESRM Accounts" in roles and not roles.intersection({"System Manager", "ESRM Approver", "HR Manager"}):
        return "`tabEmployee Advance`.docstatus = 1"
    if _is_privileged(user) or not (_roles(user) & EMPLOYEE_ROLES):
        return None
    return _employee_condition(user).format(doctype="Employee Advance")


def expense_claim_query_conditions(user=None):
    user = user or frappe.session.user
    if _is_privileged(user) or not (_roles(user) & EMPLOYEE_ROLES):
        return None
    return _employee_condition(user).format(doctype="Expense Claim")


def _has_employee_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if _is_privileged(user) or not (_roles(user) & EMPLOYEE_ROLES):
        return None
    if permission_type == "create" or not getattr(doc, "employee", None):
        return True
    return doc.employee == _employee_for_user(user) or doc.owner == user


def employee_advance_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    roles = _roles(user)
    if user != "Administrator" and "ESRM Accounts" in roles and not roles.intersection({"System Manager", "ESRM Approver", "HR Manager"}):
        if permission_type in {"read", "write", "print", "email", "export", "report", "select", None}:
            return doc.docstatus == 1
    return _has_employee_permission(doc, user, permission_type)


def expense_claim_has_permission(doc, user=None, permission_type=None):
    return _has_employee_permission(doc, user, permission_type)


def update_due_date_from_payment_entry(doc):
    for row in doc.get("references", []):
        if row.reference_doctype != "Employee Advance" or not row.reference_name:
            continue
        existing_due_date = frappe.db.get_value(
            "Employee Advance", row.reference_name, "custom_settlement_due_date"
        )
        if not existing_due_date:
            frappe.db.set_value(
                "Employee Advance", row.reference_name, "custom_settlement_due_date",
                add_days(doc.posting_date, 7), update_modified=False,
            )
        update_cash_advance_status(row.reference_name)


def on_submit_expense_claim(doc, method=None):
    if doc.custom_cash_advance:
        update_cash_advance_status(doc.custom_cash_advance)


def on_cancel_expense_claim(doc, method=None):
    if doc.custom_cash_advance:
        update_cash_advance_status(doc.custom_cash_advance)


def on_submit_journal_entry(doc, method=None):
    _refresh_advances_from_journal_entry(doc)


def on_cancel_journal_entry(doc, method=None):
    _refresh_advances_from_journal_entry(doc)


def _refresh_advances_from_journal_entry(doc):
    advances = {
        row.reference_name for row in doc.get("accounts", [])
        if row.reference_type == "Employee Advance" and row.reference_name
    }
    for advance in advances:
        update_cash_advance_status(advance)


def update_cash_advance_status(name):
    data = frappe.db.get_value(
        "Employee Advance", name,
        ["docstatus", "workflow_state", "advance_amount", "paid_amount", "claimed_amount", "return_amount", "custom_settlement_due_date"],
        as_dict=True,
    )
    if not data:
        return
    if data.docstatus == 2:
        status = "Cancelled"
    elif data.docstatus == 0:
        status = data.workflow_state or "Draft"
    elif flt(data.paid_amount) <= 0:
        status = "Approved - Awaiting Disbursement"
    else:
        outstanding = max(flt(data.paid_amount) - flt(data.claimed_amount) - flt(data.return_amount), 0)
        if outstanding <= 0:
            status = "Settled"
        elif data.custom_settlement_due_date and getdate(data.custom_settlement_due_date) < getdate(nowdate()):
            status = "Overdue"
        elif flt(data.claimed_amount) > 0:
            status = "Cash Return Due"
        elif flt(data.paid_amount) < flt(data.advance_amount):
            status = "Partially Disbursed"
        else:
            status = "Disbursed"
    frappe.db.set_value("Employee Advance", name, "custom_cash_status", status, update_modified=False)


def refresh_overdue_cash_advances():
    names = frappe.get_all("Employee Advance", filters={"docstatus": 1}, pluck="name")
    for name in names:
        update_cash_advance_status(name)


@frappe.whitelist()
def make_cash_expense_claim(employee_advance):
    advance = frappe.get_doc("Employee Advance", employee_advance)
    advance.check_permission("read")
    if advance.docstatus != 1 or flt(advance.paid_amount) <= flt(advance.claimed_amount) + flt(advance.return_amount):
        frappe.throw(_("This advance has no paid, unsettled amount."))
    from hrms.hr.doctype.expense_claim.expense_claim import get_expense_claim

    return get_expense_claim(
        employee_name=advance.employee,
        company=advance.company,
        employee_advance_name=advance.name,
        posting_date=nowdate(),
        paid_amount=advance.paid_amount,
        claimed_amount=advance.claimed_amount,
        return_amount=advance.return_amount,
    )
