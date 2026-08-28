from html import escape

import frappe
from frappe.utils import fmt_money, formatdate, get_url


INVOICE_PRINT_FORMAT = "ESRM Ticket Invoice"
RECEIPT_PRINT_FORMAT = "ESRM Money Receipt"


def queue_invoice_email(doc):
    if doc.docstatus != 1 or getattr(doc, "is_return", False):
        return
    frappe.enqueue(
        "esrm_travel.customer_document_email.send_invoice_email",
        queue="short",
        enqueue_after_commit=True,
        invoice_name=doc.name,
    )


def queue_money_receipt_email(doc):
    if (
        doc.docstatus != 1
        or doc.payment_type != "Receive"
        or doc.party_type != "Customer"
        or not doc.party
    ):
        return
    frappe.enqueue(
        "esrm_travel.customer_document_email.send_money_receipt_email",
        queue="short",
        enqueue_after_commit=True,
        payment_entry_name=doc.name,
    )


def send_invoice_email(invoice_name):
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    if invoice.docstatus != 1 or invoice.is_return:
        return
    recipient = get_customer_email(invoice.customer, invoice.contact_email)
    if not recipient:
        _log_missing_email("Sales Invoice", invoice.name, invoice.customer)
        return

    display_number = invoice.get("esrm_invoice_number") or invoice.name
    currency = invoice.currency or "BDT"
    pdf = frappe.get_print(
        "Sales Invoice", invoice.name, print_format=INVOICE_PRINT_FORMAT, as_pdf=True
    )
    message = """
        <p>Dear {customer},</p>
        <p>Please find attached invoice <strong>{number}</strong>, dated {date}, for
        <strong>{amount}</strong>.</p>
        <p>You may also review the transaction in ESRM using the link below.</p>
        <p><a href="{url}" style="background:#0b7285;color:#fff;padding:10px 16px;
        text-decoration:none;border-radius:4px;">View Invoice</a></p>
        <p>Regards,<br>Ezzy Services &amp; Resource Management</p>
    """.format(
        customer=escape(invoice.customer_name or invoice.customer),
        number=escape(display_number),
        date=formatdate(invoice.posting_date, "dd MMM yyyy"),
        amount=fmt_money(invoice.grand_total, currency=currency),
        url=escape(get_url(f"/app/sales-invoice/{invoice.name}"), quote=True),
    )
    frappe.sendmail(
        recipients=[recipient],
        subject=f"Invoice {display_number} - Ezzy Services & Resource Management",
        message=message,
        attachments=[{"fname": f"Invoice-{display_number}.pdf", "fcontent": pdf}],
        reference_doctype="Sales Invoice",
        reference_name=invoice.name,
    )


def send_money_receipt_email(payment_entry_name):
    payment = frappe.get_doc("Payment Entry", payment_entry_name)
    if (
        payment.docstatus != 1
        or payment.payment_type != "Receive"
        or payment.party_type != "Customer"
    ):
        return
    recipient = get_customer_email(payment.party)
    if not recipient:
        _log_missing_email("Payment Entry", payment.name, payment.party)
        return

    currency = payment.paid_to_account_currency or "BDT"
    pdf = frappe.get_print(
        "Payment Entry", payment.name, print_format=RECEIPT_PRINT_FORMAT, as_pdf=True
    )
    message = """
        <p>Dear {customer},</p>
        <p>Thank you. We have recorded your payment of <strong>{amount}</strong>
        on {date}. Your system-generated money receipt <strong>{receipt}</strong>
        is attached.</p>
        <p><a href="{url}" style="background:#0b7285;color:#fff;padding:10px 16px;
        text-decoration:none;border-radius:4px;">View Payment</a></p>
        <p>Regards,<br>Ezzy Services &amp; Resource Management</p>
    """.format(
        customer=escape(payment.party_name or payment.party),
        amount=fmt_money(payment.received_amount, currency=currency),
        date=formatdate(payment.posting_date, "dd MMM yyyy"),
        receipt=escape(payment.name),
        url=escape(get_url(f"/app/payment-entry/{payment.name}"), quote=True),
    )
    frappe.sendmail(
        recipients=[recipient],
        subject=f"Money Receipt {payment.name} - Ezzy Services & Resource Management",
        message=message,
        attachments=[{"fname": f"Money-Receipt-{payment.name}.pdf", "fcontent": pdf}],
        reference_doctype="Payment Entry",
        reference_name=payment.name,
    )


def get_customer_email(customer, preferred_email=None):
    if preferred_email:
        return preferred_email.strip()
    if not customer:
        return None

    result = frappe.db.sql(
        """
        select c.email_id
        from `tabContact` c
        inner join `tabDynamic Link` dl
            on dl.parent = c.name and dl.parenttype = 'Contact'
        where dl.link_doctype = 'Customer'
          and dl.link_name = %(customer)s
          and ifnull(c.email_id, '') != ''
        order by c.is_primary_contact desc, c.modified desc
        limit 1
        """,
        {"customer": customer},
    )
    return result[0][0].strip() if result else None


def _log_missing_email(doctype, name, customer):
    frappe.log_error(
        f"No customer email is configured for Customer {customer}. Document {doctype} {name} was not emailed.",
        "ESRM Customer Document Email",
    )
