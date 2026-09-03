from html import escape

import frappe
from frappe import _
from frappe.utils import fmt_money


ACCOUNTS_EMAIL = "accounts@ezzygroup.net"


def _employee_email(employee):
    return frappe.db.get_value("Employee", employee, "company_email")


def _send(recipients, subject, heading, lines):
    recipients = sorted({address for address in recipients if address})
    if not recipients:
        return
    body = "".join(f"<p>{escape(str(line))}</p>" for line in lines)
    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=f"<h3>{escape(heading)}</h3>{body}",
        now=False,
    )


def notify_employee_advance_update(doc, method=None):
    if doc.is_new() or not doc.has_value_changed("workflow_state"):
        return
    state = doc.workflow_state
    employee_email = _employee_email(doc.employee)
    amount = fmt_money(doc.advance_amount, currency=doc.currency or "BDT")
    common = [
        f"Employee: {doc.employee_name}",
        f"Advance request: {doc.name}",
        f"Amount: {amount}",
        f"Purpose: {doc.purpose}",
    ]
    if state == "Pending Approval":
        _send(
            [employee_email],
            f"Cash advance submitted — {doc.employee_name}",
            "Cash advance submitted for approval",
            common,
        )
    elif state == "Approved":
        _send(
            [employee_email],
            f"Cash advance approved — {doc.employee_name}",
            "Your cash advance has been approved",
            common + ["Accounts will record the disbursement when the cash is issued."],
        )
        _send(
            [ACCOUNTS_EMAIL],
            f"Cash disbursement required — {doc.employee_name}",
            "Admin-approved cash advance",
            common + ["Please open the approved advance and record the disbursement."],
        )
    elif state == "Rejected":
        _send(
            [employee_email],
            f"Cash advance requires revision — {doc.employee_name}",
            "Cash advance was not approved",
            common + ["Please review the request and revise it if required."],
        )


def notify_expense_claim_update(doc, method=None):
    if not doc.custom_cash_advance or doc.is_new() or not doc.has_value_changed("custom_cash_settlement_state"):
        return
    state = doc.custom_cash_settlement_state
    employee_email = _employee_email(doc.employee)
    amount = fmt_money(doc.total_claimed_amount, currency="BDT")
    common = [
        f"Employee: {doc.employee_name}",
        f"Expense settlement: {doc.name}",
        f"Cash advance: {doc.custom_cash_advance}",
        f"Claimed amount: {amount}",
    ]
    if state == "Accounts Review":
        _send(
            [ACCOUNTS_EMAIL],
            f"Expense settlement review required — {doc.employee_name}",
            "Cash advance settlement requires Accounts review",
            common + ["The submitted expenses exceed the available advance."],
        )
    elif state == "Submitted":
        _send(
            [employee_email],
            f"Expense settlement recorded — {doc.employee_name}",
            "Expense settlement recorded",
            common,
        )
    elif state == "Rejected":
        _send(
            [employee_email],
            f"Expense settlement requires revision — {doc.employee_name}",
            "Expense settlement returned for revision",
            common,
        )
