import frappe


COMPANY = "Ezzy Services & Resource Management"
PAYROLL_PAYABLE_ACCOUNT = "Employee Salary Payable - ESRM"
SALARY_EXPENSE_ACCOUNT = "Salary & Allowances - ESRM"


def setup_hrms():
    if "hrms" not in frappe.get_installed_apps():
        return

    ensure_gender_records()
    configure_company_payroll_account()
    configure_basic_salary_account()


def ensure_gender_records():
    for gender in ("Female", "Male", "Other"):
        if not frappe.db.exists("Gender", gender):
            frappe.get_doc(
                {
                    "doctype": "Gender",
                    "gender": gender,
                }
            ).insert(ignore_permissions=True)


def configure_company_payroll_account():
    if not frappe.db.exists("Company", COMPANY):
        return
    if not frappe.db.exists("Account", PAYROLL_PAYABLE_ACCOUNT):
        return

    company = frappe.get_doc("Company", COMPANY)
    if company.default_payroll_payable_account != PAYROLL_PAYABLE_ACCOUNT:
        company.default_payroll_payable_account = PAYROLL_PAYABLE_ACCOUNT
        company.save(ignore_permissions=True)

    # ERPNext marks the account as Payable while validating the Company
    # default, but HRMS requires the payroll payable account to have no type.
    if frappe.db.get_value("Account", PAYROLL_PAYABLE_ACCOUNT, "account_type"):
        frappe.db.set_value(
            "Account",
            PAYROLL_PAYABLE_ACCOUNT,
            "account_type",
            "",
            update_modified=False,
        )


def configure_basic_salary_account():
    if not frappe.db.exists("Salary Component", "Basic"):
        return
    if not frappe.db.exists("Account", SALARY_EXPENSE_ACCOUNT):
        return

    component = frappe.get_doc("Salary Component", "Basic")
    account_row = next(
        (row for row in component.accounts if row.company == COMPANY),
        None,
    )
    if account_row:
        account_row.account = SALARY_EXPENSE_ACCOUNT
    else:
        component.append(
            "accounts",
            {
                "company": COMPANY,
                "account": SALARY_EXPENSE_ACCOUNT,
            },
        )
    component.save(ignore_permissions=True)
