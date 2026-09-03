import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from esrm_travel.chart_of_accounts import COMPANY, get_account_name


ACCOUNTS_ROLE = "ESRM Accounts"
ADVANCE_ACCOUNT = "Staff Cash Advances - ESRM"
OLD_ADVANCE_ACCOUNTS = (
    "Employee Advances - ESRM",
    "Employee Control Ledger/Staff Advance - ESRM",
)
EXPENSE_TYPES = (
    ("Local Conveyance", "Local Conveyance"),
    ("Travel and Daily Allowance", "TA & DA"),
    ("Fuel", "Fuel Cost"),
    ("Courier", "Courier Cost"),
    ("Mobile Bill", "Mobile Bill"),
    ("Printing and Stationery", "Printing  Stationery"),
    ("Entertainment", "Entertainment"),
    ("Office Maintenance", "Office Maintenance Expenses"),
    ("IT Expense", "IT Expenses"),
    ("Miscellaneous", "Miscellaneous Expenses"),
    ("Revenue Stamp", "Revenue Stamp"),
    ("Canteen", "Canteen Expenses"),
    ("Medical", "Medical Expenses"),
)


def setup_cash_advance_module():
    if not frappe.db.exists("DocType", "Employee Advance"):
        return
    setup_custom_fields()
    setup_company_defaults()
    setup_expense_types()
    setup_workflow_masters()
    setup_employee_advance_workflow()
    setup_expense_claim_workflow()
    disable_unused_advance_accounts()


def setup_custom_fields():
    create_custom_fields(
        {
            "Employee Advance": [
                {
                    "fieldname": "custom_settlement_due_date",
                    "label": "Settlement Due Date",
                    "fieldtype": "Date",
                    "insert_after": "advance_amount",
                    "read_only": 1,
                    "in_list_view": 1,
                    "description": "Automatically set to seven days after the first disbursement.",
                },
                {
                    "fieldname": "custom_cash_status",
                    "label": "Cash Status",
                    "fieldtype": "Data",
                    "insert_after": "status",
                    "read_only": 1,
                    "allow_on_submit": 1,
                    "in_list_view": 1,
                    "in_standard_filter": 1,
                    "no_copy": 1,
                },
            ],
            "Expense Claim": [
                {
                    "fieldname": "custom_cash_advance",
                    "label": "Cash Advance",
                    "fieldtype": "Link",
                    "options": "Employee Advance",
                    "insert_after": "employee_name",
                    "read_only": 1,
                    "in_list_view": 1,
                },
                {
                    "fieldname": "custom_settlement_variance",
                    "label": "Expense Variance",
                    "fieldtype": "Currency",
                    "options": "Company:company:default_currency",
                    "insert_after": "total_advance_amount",
                    "read_only": 1,
                    "description": "Positive means reimbursement review; negative means cash return due.",
                },
                {
                    "fieldname": "custom_cash_settlement_state",
                    "label": "Cash Settlement State",
                    "fieldtype": "Link",
                    "options": "Workflow State",
                    "insert_after": "approval_status",
                    "read_only": 1,
                    "allow_on_submit": 1,
                    "no_copy": 1,
                },
            ],
            "Expense Claim Detail": [
                {
                    "fieldname": "custom_receipt_attachment",
                    "label": "Receipt / Supporting Document",
                    "fieldtype": "Attach",
                    "insert_after": "description",
                    "in_list_view": 1,
                    "description": "Attach the receipt, invoice, voucher, or other evidence for this expense row.",
                },
            ],
        },
        update=True,
    )


def setup_company_defaults():
    if frappe.db.exists("Company", COMPANY) and frappe.db.exists("Account", ADVANCE_ACCOUNT):
        frappe.db.set_value(
            "Company", COMPANY, "default_employee_advance_account", ADVANCE_ACCOUNT,
            update_modified=False,
        )
        payable_account = "Employee Salary Payable - ESRM"
        if frappe.db.exists("Account", payable_account):
            frappe.db.set_value(
                "Company", COMPANY, "default_expense_claim_payable_account", payable_account,
                update_modified=False,
            )


def setup_expense_types():
    if not frappe.db.exists("DocType", "Expense Claim Type"):
        return
    for expense_type, account_name in EXPENSE_TYPES:
        account = get_account_name(account_name)
        if not frappe.db.exists("Account", account):
            continue
        if frappe.db.exists("Expense Claim Type", expense_type):
            doc = frappe.get_doc("Expense Claim Type", expense_type)
        else:
            doc = frappe.get_doc({"doctype": "Expense Claim Type", "expense_type": expense_type})
        row = next((row for row in doc.get("accounts", []) if row.company == COMPANY), None)
        if row:
            row.default_account = account
        else:
            doc.append("accounts", {"company": COMPANY, "default_account": account})
        if doc.is_new():
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)


def setup_workflow_masters():
    states = {
        "Draft": (0, "Primary"),
        "Pending Approval": (0, "Warning"),
        "Approved": (1, "Success"),
        "Rejected": (0, "Danger"),
        "Accounts Review": (0, "Warning"),
        "Submitted": (1, "Success"),
    }
    for name, (doc_status, style) in states.items():
        if frappe.db.exists("Workflow State", name):
            continue
        frappe.get_doc(
            {
                "doctype": "Workflow State",
                "workflow_state_name": name,
                "doc_status": doc_status,
                "style": style,
            }
        ).insert(ignore_permissions=True)

    for action in ("Send for Approval", "Approve", "Reject", "Submit Settlement", "Send to Accounts", "Finalize Settlement", "Revise"):
        if not frappe.db.exists("Workflow Action Master", action):
            frappe.get_doc(
                {"doctype": "Workflow Action Master", "workflow_action_name": action}
            ).insert(ignore_permissions=True)


def setup_employee_advance_workflow():
    _save_workflow(
        "Employee Cash Advance Approval",
        "Employee Advance",
        "workflow_state",
        [
            _state("Draft", "Employee", 0),
            _state("Pending Approval", "ESRM Approver", 0),
            _state("Approved", ACCOUNTS_ROLE, 1),
            _state("Rejected", "Employee", 0, optional=1),
        ],
        [
            _transition("Draft", "Send for Approval", "Employee", "Pending Approval", self_approval=1),
            _transition("Pending Approval", "Approve", "ESRM Approver", "Approved"),
            _transition("Pending Approval", "Reject", "ESRM Approver", "Rejected"),
            _transition("Rejected", "Revise", "Employee", "Draft", self_approval=1),
        ],
    )


def setup_expense_claim_workflow():
    _save_workflow(
        "Employee Cash Expense Settlement",
        "Expense Claim",
        "custom_cash_settlement_state",
        [
            _state("Draft", "Employee", 0),
            _state("Accounts Review", ACCOUNTS_ROLE, 0),
            _state("Submitted", "Employee", 1),
            _state("Rejected", "Employee", 0, optional=1),
        ],
        [
            _transition(
                "Draft", "Submit Settlement", "Employee", "Submitted",
                condition="doc.custom_settlement_variance <= 0", self_approval=1,
            ),
            _transition(
                "Draft", "Send to Accounts", "Employee", "Accounts Review",
                condition="doc.custom_settlement_variance > 0", self_approval=1,
            ),
            _transition("Accounts Review", "Finalize Settlement", ACCOUNTS_ROLE, "Submitted"),
            _transition("Accounts Review", "Reject", ACCOUNTS_ROLE, "Rejected"),
            _transition("Rejected", "Revise", "Employee", "Draft", self_approval=1),
        ],
    )


def _state(name, role, doc_status, optional=0):
    return {
        "state": name, "allow_edit": role, "doc_status": str(doc_status),
        "is_optional_state": optional,
    }


def _transition(state, action, role, next_state, condition=None, self_approval=0):
    row = {
        "state": state, "action": action, "allowed": role, "next_state": next_state,
        "allow_self_approval": self_approval,
    }
    if condition:
        row["condition"] = condition
    return row


def _save_workflow(name, document_type, state_field, states, transitions):
    if frappe.db.exists("Workflow", name):
        doc = frappe.get_doc("Workflow", name)
    else:
        doc = frappe.get_doc({"doctype": "Workflow", "workflow_name": name})
    doc.document_type = document_type
    doc.workflow_state_field = state_field
    doc.is_active = 1
    doc.override_status = 0
    doc.send_email_alert = 0
    doc.set("states", states)
    doc.set("transitions", transitions)
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)


def disable_unused_advance_accounts():
    for account in OLD_ADVANCE_ACCOUNTS:
        if account == ADVANCE_ACCOUNT or not frappe.db.exists("Account", account):
            continue
        active_entries = frappe.db.count("GL Entry", {"account": account, "is_cancelled": 0})
        if active_entries:
            frappe.log_error(
                f"Did not disable {account}: it has {active_entries} active GL entries.",
                "Cash Advance Account Consolidation",
            )
            continue
        frappe.db.set_value("Account", account, "disabled", 1, update_modified=False)
