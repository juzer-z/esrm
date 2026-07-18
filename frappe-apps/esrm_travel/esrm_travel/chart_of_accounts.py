import frappe


COMPANY = "Ezzy Services and resources Management"
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
    ("Supplier Control Ledger", "Current Liabilities - ESRM", "Payable"),
    ("Bank Loan", "Loans (Liabilities) - ESRM", ""),
    ("Operating Income", "Direct Income - ESRM", ""),
    ("Non Operating Income", "Indirect Income - ESRM", ""),
    ("COGS Raw Materials", "Direct Expenses - ESRM", "Cost of Goods Sold"),
    ("COGS Others", "Direct Expenses - ESRM", "Cost of Goods Sold"),
    ("Office Expenses", "Indirect Expenses - ESRM", ""),
    ("Salary & Remuneration", "Indirect Expenses - ESRM", ""),
    ("Fees & Renewal Fees", "Indirect Expenses - ESRM", ""),
    ("Recruitment Expenses", "Indirect Expenses - ESRM", ""),
    ("Transport Expenses", "Indirect Expenses - ESRM", ""),
    ("Tax and Govt Fee", "Indirect Expenses - ESRM", "Tax"),
    ("Selling and Marketing Expense", "Indirect Expenses - ESRM", ""),
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
    ("Employee Control Ledger", "Advance, Deposit and Pre-Payments", ""),
    ("Earnest & Security Money", "Advance, Deposit and Pre-Payments", ""),
    ("Tender Deposit", "Advance, Deposit and Pre-Payments", ""),
    ("Advance Against Rent", "Advance, Deposit and Pre-Payments", ""),
    ("BG & PG (Margin)", "Advance, Deposit and Pre-Payments", ""),
    ("General Stock", "Inventories/ Stock", "Stock"),
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
    ("Licenses and Permits", "Intangible Asset", "Fixed Asset"),
    ("Mr Zulfikar Ali (Share Capital)", "Share Capital", "Equity"),
    ("Mr Shabbir Hussain (Share Capital)", "Share Capital", "Equity"),
    ("Mr Shahnul Hasan Khan (Share Capital)", "Share Capital", "Equity"),
    ("Employee Salary Payable", "Accounts Payable", "Payable"),
    ("Office Rent Payable", "Accounts Payable", "Payable"),
    ("Audit Fees Payable", "Accounts Payable", "Payable"),
    ("Legal Fees Payable", "Accounts Payable", "Payable"),
    ("TDS Payable", "Accounts Payable", "Tax"),
    ("VDS Payable", "Accounts Payable", "Tax"),
    ("Air Ticket Purchase International Payable", "Supplier Control Ledger", "Payable"),
    ("Air Ticket Purchase Domestic Payable", "Supplier Control Ledger", "Payable"),
    ("Bank Ltd.", "Bank Loan", ""),
    ("Air Ticket Sales-International", "Operating Income", ""),
    ("Visa and Other Service-Sales", "Operating Income", ""),
    ("Manpower Fee", "Operating Income", ""),
    ("Incentive Income", "Operating Income", ""),
    ("Unallocate Revenue income", "Non Operating Income", ""),
    ("Interest Income On FDR", "Non Operating Income", ""),
    ("Air Ticket Purchase- International", "COGS Raw Materials", "Cost of Goods Sold"),
    ("Air Ticket Purchase -Domestic", "COGS Raw Materials", "Cost of Goods Sold"),
    ("Visa & Others Expenses(Foreign Employee)", "COGS Raw Materials", "Cost of Goods Sold"),
    ("Extra Bagges", "COGS Others", "Cost of Goods Sold"),
    ("Work Permit & Security Clearance", "COGS Others", "Cost of Goods Sold"),
    ("Visa & Other Service Expenses(Local)", "COGS Others", "Cost of Goods Sold"),
    ("Visa & Other Service Expenses(Foreigner)", "COGS Others", "Cost of Goods Sold"),
    ("Office Entertainment", "Office Expenses", ""),
    ("Office TA & DA", "Office Expenses", ""),
    ("Office Courier Cost", "Office Expenses", ""),
    ("DOHS Council Bill", "Office Expenses", ""),
    ("Medical Expenses", "Office Expenses", ""),
    ("Office Equipment Maintenance", "Office Expenses", ""),
    ("Gift  & Donation", "Office Expenses", ""),
    ("Revenue Stamp", "Office Expenses", ""),
    ("Complementary Expenses", "Office Expenses", ""),
    ("Canteen Expenses", "Office Expenses", ""),
    ("IT Expenses", "Office Expenses", ""),
    ("Insurance", "Office Expenses", ""),
    ("Mobile Bill", "Office Expenses", ""),
    ("TAX on Office Rent", "Office Expenses", "Tax"),
    ("VAT on Office Rent", "Office Expenses", "Tax"),
    ("Office Printing Expenses", "Office Expenses", ""),
    ("Office CSR Expenses", "Office Expenses", ""),
    ("Salary & Allowances", "Salary & Remuneration", ""),
    ("Bonus for Eid Ul Azha", "Salary & Remuneration", ""),
    ("Bonus for Eid-Ul-Fitar", "Salary & Remuneration", ""),
    ("Incentive", "Salary & Remuneration", ""),
    ("PF-Company's Cont (50%)", "Salary & Remuneration", ""),
    ("Others Allowances", "Salary & Remuneration", ""),
    ("License Fee", "Fees & Renewal Fees", ""),
    ("Membership Fee", "Fees & Renewal Fees", ""),
    ("Trade License Renewal Fee", "Fees & Renewal Fees", ""),
    ("Audit Fees Expense", "Fees & Renewal Fees", ""),
    ("ID card & Visiting Card", "Recruitment Expenses", ""),
    ("Fuel Cost", "Transport Expenses", ""),
    ("Vahicle maintenance", "Transport Expenses", ""),
    ("Rent vehicle", "Transport Expenses", ""),
    ("TDS", "Tax and Govt Fee", "Tax"),
    ("VDS", "Tax and Govt Fee", "Tax"),
    ("Tax Expenses", "Tax and Govt Fee", "Tax"),
    ("Advertisment Expenses", "Selling and Marketing Expense", ""),
    ("Promotional Expenses", "Selling and Marketing Expense", ""),
    ("Tender Expenses-PG-Charge & Commission", "Selling and Marketing Expense", ""),
    ("Bank Charge & Commission", "Financial Expenses", ""),
    ("Loan Processing Expenses", "Financial Expenses", ""),
    ("Credit Rating Fee", "Financial Expenses", ""),
]


def setup_chart_of_accounts():
    if not frappe.db.exists("Company", COMPANY):
        return

    for account_name, parent_account, account_type in ACCOUNT_GROUPS:
        ensure_account(account_name, parent_account, account_type, is_group=1)

    for account_name, parent_group_name, account_type in ACCOUNT_LEDGERS:
        parent_account = get_account_name(parent_group_name)
        if parent_account:
            ensure_account(account_name, parent_account, account_type, is_group=0)


def ensure_account(account_name, parent_account, account_type="", is_group=0):
    if frappe.db.exists("Account", get_account_name(account_name)):
        return get_account_name(account_name)

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
            "company": COMPANY,
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


def get_account_name(account_name):
    return f"{account_name.strip()} - {ABBR}"
