import frappe


COMPANY = "Ezzy Services & Resource Management"
COMPANY_ALIASES = (
    "Ezzy Services and resources Management",
    "Ezzy Services & Resources Management",
)
ABBR = "ESRM"


ACCOUNT_GROUPS = [
    ("Cash In Hand", "Current Assets - ESRM", "Cash"),
    ("Cash At Bank", "Current Assets - ESRM", "Bank"),
    ("Fixed Deposit Accounts", "Investments - ESRM", ""),
    ("Accounts/ Trade Receivable", "Current Assets - ESRM", "Receivable"),
    ("Advance, Deposit and Pre-Payments", "Current Assets - ESRM", ""),
    ("Inventories/ Stock", "Stock Assets - ESRM", "Stock"),
    ("Inter Company Transaction", "Current Assets - ESRM", ""),
    ("Director Expenses Account ( STL)", "Current Assets - ESRM", ""),
    ("Fixed Assets", "Application of Funds (Assets) - ESRM", ""),
    ("Intangible Asset", "Fixed Assets - ESRM", "Fixed Asset"),
    ("Share Capital", "Equity - ESRM", "Equity"),
    ("Accounts Payable", "Current Liabilities - ESRM", "Payable"),
    ("Supplier Control Ledger/ Trade Payable", "Accounts Payable - ESRM", "Payable"),
    ("Bank Loan", "Loans (Liabilities) - ESRM", ""),
    ("Operating Income", "Direct Income - ESRM", ""),
    ("Non Operating Income", "Indirect Income - ESRM", ""),
    ("COST OF SERVICES", "Direct Expenses - ESRM", "Cost of Goods Sold"),
    ("Administrative Expense", "Indirect Expenses - ESRM", ""),
    ("Operating Expenses", "Indirect Expenses - ESRM", ""),
    ("Salary & Remuneration", "Operating Expenses - ESRM", ""),
    ("Fees & Renewal Fees", "Operating Expenses - ESRM", ""),
    ("Recruitment Expenses", "Operating Expenses - ESRM", ""),
    ("Transport Expenses", "Operating Expenses - ESRM", ""),
    ("Tax and Govt Fee", "Operating Expenses - ESRM", "Tax"),
    ("Selling and Marketing Expense", "Operating Expenses - ESRM", ""),
    ("Depreciation Expenses", "Indirect Expenses - ESRM", ""),
    ("Financial Expenses", "Indirect Expenses - ESRM", ""),
]


ACCOUNT_LEDGERS = [
    ("Petty Cash", "Cash In Hand", "Cash"),
    ("Dhaka Bank (Gulshan Br)-2151000012910.", "Cash At Bank", "Bank"),
    ("Premier Bank-0199", "Cash At Bank", "Bank"),
    ("NCCBL  Bank-2528", "Cash At Bank", "Bank"),
    ("DBBL Bank-3779", "Cash At Bank", "Bank"),
    ("SBAC-Mohakhali-0081111002597", "Cash At Bank", "Bank"),
    ("Pubali Bank-Mohakhali-3677901032084", "Cash At Bank", "Bank"),
    ("Pubali Bank-3677102002657 (Mohakhali Corp. Branch)", "Cash At Bank", "Bank"),
    ("FDR-A/c", "Fixed Deposit Accounts", "Bank"),
    ("Accounts Receivable (E Enterprise)", "Accounts/ Trade Receivable", "Receivable"),
    ("Accounts Receivable - Air Ticket", "Accounts/ Trade Receivable", "Receivable"),
    ("Accounts Receivable -Work Permit", "Accounts/ Trade Receivable", "Receivable"),
    ("Others Receivable", "Accounts/ Trade Receivable", "Receivable"),
    ("Employee Control Ledger/Staff Advance", "Advance, Deposit and Pre-Payments", ""),
    ("Earnest & Security Deposit", "Advance, Deposit and Pre-Payments", ""),
    ("Advance Income Tax(AIT)", "Advance, Deposit and Pre-Payments", "Tax"),
    ("Advance Against Rent", "Advance, Deposit and Pre-Payments", ""),
    ("BG & PG (Margin)", "Advance, Deposit and Pre-Payments", ""),
    ("General Stock/Office Stationery", "Inventories/ Stock", "Stock"),
    ("Ezzy Group", "Inter Company Transaction", ""),
    ("Ezzy Automations Limited", "Inter Company Transaction", ""),
    ("Ezzy Enterprise", "Inter Company Transaction", ""),
    ("Ezzy Solutions Ltd", "Inter Company Transaction", ""),
    ("EZZY ENERGY (Partnership)", "Inter Company Transaction", ""),
    ("Zulfikar Ali Sir Exp. Ac", "Director Expenses Account ( STL)", ""),
    ("Shabbir Hussain Sir Exp. Acc", "Director Expenses Account ( STL)", ""),
    ("Mr.Zahir Uddin Swapan Exp.Ac", "Director Expenses Account ( STL)", ""),
    ("Ali Asger Zulfikar Ali  Sir Expenses Ac", "Director Expenses Account ( STL)", ""),
    ("IT & Electronics Equipment", "Fixed Assets", "Fixed Asset"),
    ("Furniture & Fixture", "Fixed Assets", "Fixed Asset"),
    ("Office Equipment", "Fixed Assets", "Fixed Asset"),
    ("Vehicles", "Fixed Assets", "Fixed Asset"),
    ("Goodwill", "Intangible Asset", "Fixed Asset"),
    ("Licenses and Permits (BMET License)", "Intangible Asset", "Fixed Asset"),
    ("Software/Website", "Intangible Asset", "Fixed Asset"),
    ("Mr Zulfikar Ali (Share Capital)", "Share Capital", "Equity"),
    ("Mr Shabbir Hussain (Share Capital)", "Share Capital", "Equity"),
    ("Mr Shahnul Hasan Khan (Share Capital)", "Share Capital", "Equity"),
    ("Employee Salary Payable", "Accounts Payable", "Payable"),
    ("Office Rent Payable", "Accounts Payable", "Payable"),
    ("Utility Payable", "Accounts Payable", "Payable"),
    ("Audit Fees Payable", "Accounts Payable", "Payable"),
    ("Legal Fees Payable", "Accounts Payable", "Payable"),
    ("TDS Payable", "Accounts Payable", "Tax"),
    ("VDS Payable", "Accounts Payable", "Tax"),
    ("Air Ticket Supplier Payable (International)", "Supplier Control Ledger/ Trade Payable", "Payable"),
    ("Air Ticket Supplier Payable (Domestic)", "Supplier Control Ledger/ Trade Payable", "Payable"),
    ("Overdraft", "Bank Loan", ""),
    ("Short Term Loan", "Bank Loan", ""),
    ("Long Term Loan", "Bank Loan", ""),
    ("Bank Ltd.", "Bank Loan", ""),
    ("Air Ticket Sales-International", "Operating Income", ""),
    ("Visa and Other Service-Sales", "Operating Income", ""),
    ("Manpower Fee", "Operating Income", ""),
    ("Incentive Income", "Operating Income", ""),
    ("Unallocate Revenue income", "Non Operating Income", ""),
    ("Penalty & Fine", "Non Operating Income", ""),
    ("Interest Income On FDR", "Non Operating Income", ""),
    ("Air Ticket Purchase- International", "COST OF SERVICES", "Cost of Goods Sold"),
    ("Air Ticket Purchase -Domestic", "COST OF SERVICES", "Cost of Goods Sold"),
    ("Visa & Others Expenses(Foreign Employee)", "COST OF SERVICES", "Cost of Goods Sold"),
    ("Visa & Other Service Expenses(Local)", "COST OF SERVICES", "Cost of Goods Sold"),
    ("Embassy Fee", "COST OF SERVICES", "Cost of Goods Sold"),
    ("BMET Registration", "COST OF SERVICES", "Cost of Goods Sold"),
    ("Work Permit & Security Clearance", "COST OF SERVICES", "Cost of Goods Sold"),
    ("Extra Bagges", "COST OF SERVICES", "Cost of Goods Sold"),
    ("Candidate Training Cost", "COST OF SERVICES", "Cost of Goods Sold"),
    ("Office Rent", "Administrative Expense", ""),
    ("Electricity", "Administrative Expense", ""),
    ("Entertainment", "Administrative Expense", ""),
    ("TA & DA", "Administrative Expense", ""),
    ("Courier Cost", "Administrative Expense", ""),
    ("DOHS Council Bill", "Administrative Expense", ""),
    ("Medical Expenses", "Administrative Expense", ""),
    ("Office Maintenance Expenses", "Administrative Expense", ""),
    ("Office Equipment Maintenance", "Administrative Expense", ""),
    ("Gift  & Donation", "Administrative Expense", ""),
    ("Revenue Stamp", "Administrative Expense", ""),
    ("Complementary Expenses", "Administrative Expense", ""),
    ("Miscellaneous Expenses", "Administrative Expense", ""),
    ("Canteen Expenses", "Administrative Expense", ""),
    ("IT Expenses", "Administrative Expense", ""),
    ("Insurance", "Administrative Expense", ""),
    ("Mobile Bill", "Administrative Expense", ""),
    ("TAX on Office Rent", "Administrative Expense", "Tax"),
    ("VAT on Office Rent", "Administrative Expense", "Tax"),
    ("Printing  Stationery", "Administrative Expense", ""),
    ("Office CSR Expenses", "Administrative Expense", ""),
    ("Trade License Renewal Fee", "Administrative Expense", ""),
    ("Membership Fee", "Administrative Expense", ""),
    ("Recruitment License Renewal", "Administrative Expense", ""),
    ("Audit Fees", "Administrative Expense", ""),
    ("Legal Fees", "Administrative Expense", ""),
    ("Salary & Allowances", "Salary & Remuneration", ""),
    ("Bonus for Eid Ul Azha", "Salary & Remuneration", ""),
    ("Bonus for Eid-Ul-Fitar", "Salary & Remuneration", ""),
    ("Incentive", "Salary & Remuneration", ""),
    ("PF-Company's Contribution", "Salary & Remuneration", ""),
    ("Others Allowances", "Salary & Remuneration", ""),
    ("License Fee", "Fees & Renewal Fees", ""),
    ("ID card & Visiting Card", "Recruitment Expenses", ""),
    ("Fuel Cost", "Transport Expenses", ""),
    ("Vahicle maintenance", "Transport Expenses", ""),
    ("Rent vehicle", "Transport Expenses", ""),
    ("Local Conveyance", "Transport Expenses", ""),
    ("TDS", "Tax and Govt Fee", "Tax"),
    ("VDS", "Tax and Govt Fee", "Tax"),
    ("Tax Expenses", "Tax and Govt Fee", "Tax"),
    ("Advertisment Expenses", "Selling and Marketing Expense", ""),
    ("Promotional Expenses", "Selling and Marketing Expense", ""),
    ("Business Development", "Selling and Marketing Expense", ""),
    ("Trade Fair Expense", "Selling and Marketing Expense", ""),
    ("Tender Expenses-PG-Charge & Commission", "Selling and Marketing Expense", ""),
    ("Depreciation- Computer & Laptop", "Depreciation Expenses", ""),
    ("Depreciation-Furniture & Fixture", "Depreciation Expenses", ""),
    ("Depreciation-Office Equipment", "Depreciation Expenses", ""),
    ("Depreciation-Vehicles", "Depreciation Expenses", ""),
    ("Bank Charge & Commission", "Financial Expenses", ""),
    ("Loan Processing Expenses", "Financial Expenses", ""),
    ("Loan Interest", "Financial Expenses", ""),
    ("Credit Rating Fee", "Financial Expenses", ""),
]


ACCOUNT_RENAMES = [
    ("Supplier Control Ledger", "Supplier Control Ledger/ Trade Payable"),
    ("COGS Raw Materials", "COST OF SERVICES"),
    ("Office Expenses", "Administrative Expense"),
    ("Employee Control Ledger", "Employee Control Ledger/Staff Advance"),
    ("Earnest & Security Money", "Earnest & Security Deposit"),
    ("General Stock", "General Stock/Office Stationery"),
    ("Licenses and Permits", "Licenses and Permits (BMET License)"),
    ("Air Ticket Purchase International Payable", "Air Ticket Supplier Payable (International)"),
    ("Air Ticket Purchase Domestic Payable", "Air Ticket Supplier Payable (Domestic)"),
    ("Office Entertainment", "Entertainment"),
    ("Office TA & DA", "TA & DA"),
    ("Office Courier Cost", "Courier Cost"),
    ("Office Printing Expenses", "Printing  Stationery"),
    ("PF-Company's Cont (50%)", "PF-Company's Contribution"),
    ("Audit Fees Expense", "Audit Fees"),
]


def setup_chart_of_accounts():
    company = ensure_company_name()
    if not company:
        return

    rename_revised_accounts()

    for account_name, parent_account, account_type in ACCOUNT_GROUPS:
        ensure_account(account_name, parent_account, account_type, is_group=1)

    for account_name, parent_group_name, account_type in ACCOUNT_LEDGERS:
        parent_account = get_account_name(parent_group_name)
        if parent_account:
            ensure_account(account_name, parent_account, account_type, is_group=0)

    ensure_account_parent("Supplier Control Ledger/ Trade Payable", "Accounts Payable - ESRM")


def ensure_account(account_name, parent_account, account_type="", is_group=0):
    company = get_company()
    if not company:
        return None

    account_id = get_account_name(account_name)
    if frappe.db.exists("Account", account_id):
        account = frappe.get_doc("Account", account_id)
        changed = False

        if account.parent_account != parent_account and frappe.db.exists("Account", parent_account):
            account.parent_account = parent_account
            changed = True
        if account.account_type != account_type:
            account.account_type = account_type
            changed = True
        if account.is_group != is_group:
            account.is_group = is_group
            changed = True

        if changed:
            account.save(ignore_permissions=True)
        return account_id

    if not frappe.db.exists("Account", parent_account):
        frappe.log_error(f"Parent account not found: {parent_account}", "ESRM Chart of Accounts")
        return None

    parent = frappe.db.get_value(
        "Account",
        parent_account,
        ["root_type", "report_type"],
        as_dict=True,
    )

    account = frappe.get_doc(
        {
            "doctype": "Account",
            "company": company,
            "account_name": account_name.strip(),
            "parent_account": parent_account,
            "is_group": is_group,
            "root_type": parent.root_type,
            "report_type": parent.report_type,
            "account_type": account_type,
        }
    )
    account.insert(ignore_permissions=True)
    return account.name


def ensure_account_parent(account_name, parent_account):
    account_id = get_account_name(account_name)
    if not frappe.db.exists("Account", account_id) or not frappe.db.exists("Account", parent_account):
        return

    account = frappe.get_doc("Account", account_id)
    if account.parent_account == parent_account:
        return

    account.parent_account = parent_account
    account.save(ignore_permissions=True)


def rename_revised_accounts():
    for old_name, new_name in ACCOUNT_RENAMES:
        old_id = get_account_name(old_name)
        new_id = get_account_name(new_name)

        if not frappe.db.exists("Account", old_id) or frappe.db.exists("Account", new_id):
            continue

        try:
            frappe.rename_doc("Account", old_id, new_id, force=True)
            frappe.db.set_value("Account", new_id, "account_name", new_name)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"ESRM Chart Rename Failed: {old_name} to {new_name}",
            )


def get_account_name(account_name):
    return f"{account_name.strip()} - {ABBR}"


def ensure_company_name():
    if frappe.db.exists("Company", COMPANY):
        frappe.db.set_value("Company", COMPANY, "company_name", COMPANY)
        return COMPANY

    company = None
    for legacy_company in COMPANY_ALIASES:
        if frappe.db.exists("Company", legacy_company):
            company = legacy_company
            break

    if not company:
        company = frappe.db.get_value("Company", {"abbr": ABBR}, "name")

    if not company:
        return None

    if company != COMPANY:
        try:
            frappe.rename_doc("Company", company, COMPANY, force=True)
            frappe.db.set_value("Company", COMPANY, "company_name", COMPANY)
            return COMPANY
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"ESRM Company Rename Failed: {company} to {COMPANY}")
            return company

    return company


def get_company():
    if frappe.db.exists("Company", COMPANY):
        return COMPANY

    for legacy_company in COMPANY_ALIASES:
        if frappe.db.exists("Company", legacy_company):
            return legacy_company

    return frappe.db.get_value("Company", {"abbr": ABBR}, "name")
