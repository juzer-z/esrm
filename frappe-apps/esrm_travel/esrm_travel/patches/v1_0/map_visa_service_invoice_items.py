import frappe


ITEM_CODE = "VS"
ITEM_NAME = "Visa Service"
INCOME_ACCOUNT = "Visa and Other Service-Sales - ESRM"


def execute():
    if not frappe.db.exists("Item", ITEM_CODE) or not frappe.db.exists("Account", INCOME_ACCOUNT):
        return

    invoices = frappe.db.sql_list(
        """
        select distinct si.name
        from `tabSales Invoice` si
        where ifnull(si.esrm_visa_service, '') != ''
           or exists (
                select 1 from `tabESRM Invoice Visa Service` detail
                where detail.parent = si.name and ifnull(detail.visa_service, '') != ''
           )
        """
    )
    if not invoices:
        return

    frappe.db.sql(
        """
        update `tabSales Invoice Item` item
        set item.item_code = %(item_code)s,
            item.item_name = %(item_name)s,
            item.income_account = %(income_account)s
        where item.parent in %(invoices)s
        """,
        {
            "item_code": ITEM_CODE,
            "item_name": ITEM_NAME,
            "income_account": INCOME_ACCOUNT,
            "invoices": tuple(invoices),
        },
    )

    for invoice_name in invoices:
        if frappe.db.get_value("Sales Invoice", invoice_name, "docstatus") != 1:
            continue
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        invoice.repost_accounting_entries()
