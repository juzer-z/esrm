import frappe


PRINT_FORMAT_NAME = "ESRM Ticket Invoice"


def setup_print_formats():
    setup_esrm_ticket_invoice_print_format()
    ensure_invoice_print_defaults()


def setup_esrm_ticket_invoice_print_format():
    doc = get_or_create("Print Format", PRINT_FORMAT_NAME)
    doc.update(
        {
            "doc_type": "Sales Invoice",
            "module": "ESRM Travel",
            "print_format_type": "Jinja",
            "custom_format": 1,
            "disabled": 0,
            "html": ESRM_TICKET_INVOICE_HTML,
        }
    )
    save_doc(doc)


def ensure_invoice_print_defaults():
    if not frappe.db.exists("DocType", "ESRM Travel Settings"):
        return

    settings = frappe.get_single("ESRM Travel Settings")
    defaults = {
        "invoice_letterhead_address": "Ezzy Service and Resource Management Ltd",
        "invoice_payment_instructions": 'WE ARE REQUESTING YOU TO PAY THE BILL AT YOUR EARLIEST. PLEASE NOTE THAT PAYMENT WILL BE MADE IN FAVOR OF "EZZY SERVICE AND RESOURCE MANAGEMENT LTD" BY ACCOUNT PAYEE CHEQUE/ DEPOSIT TO:',
        "invoice_bank_account_number": "505-111-00000-199",
        "invoice_bank_name": "PREMIER BANK LTD.",
        "invoice_bank_branch": "BANANI SME BRANCH, DHAKA",
        "invoice_signatory_name": "U OAI MONG MARMA JOY",
        "invoice_signatory_designation": "ASSISTANT MANAGER",
    }

    changed = False
    for fieldname, value in defaults.items():
        if not settings.get(fieldname):
            settings.set(fieldname, value)
            changed = True

    if changed:
        settings.save(ignore_permissions=True)


def get_or_create(doctype, name):
    if frappe.db.exists(doctype, name):
        return frappe.get_doc(doctype, name)
    return frappe.new_doc(doctype).update({"doctype": doctype, "name": name})


def save_doc(doc):
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)


ESRM_TICKET_INVOICE_HTML = """
{% set settings = frappe.get_single("ESRM Travel Settings") %}
{% set invoice_no = doc.esrm_invoice_number or doc.name %}
{% set tickets = doc.esrm_ticket_bookings or [] %}
{% if not tickets and doc.esrm_ticket_booking %}
    {% set booking = frappe.get_doc("Ticket Booking", doc.esrm_ticket_booking) %}
    {% set tickets = [{
        "issue_date": booking.issue_date,
        "purpose": booking.purpose,
        "reference": booking.reference,
        "passenger_name": booking.passenger_name,
        "ticket_number": booking.ticket_number,
        "route": booking.route_summary,
        "carrier": booking.airline,
        "fare": booking.invoice_amount,
        "remarks": booking.remarks
    }] %}
{% endif %}

<style>
    .esrm-invoice {
        color: #111;
        font-family: Arial, sans-serif;
        font-size: 11px;
        line-height: 1.35;
    }
    .esrm-header {
        border-bottom: 2px solid #1f4e79;
        display: flex;
        gap: 18px;
        margin-bottom: 16px;
        padding-bottom: 12px;
    }
    .esrm-logo {
        max-height: 72px;
        max-width: 180px;
        object-fit: contain;
    }
    .esrm-company {
        flex: 1;
        padding-top: 4px;
    }
    .esrm-company h1 {
        color: #1f4e79;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 0;
        margin: 0 0 4px;
        text-transform: uppercase;
    }
    .esrm-company-address {
        white-space: pre-line;
    }
    .esrm-meta {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 12px;
        margin-bottom: 14px;
    }
    .esrm-meta-table {
        border-collapse: collapse;
        min-width: 210px;
    }
    .esrm-meta-table td {
        border: 1px solid #888;
        padding: 5px 7px;
    }
    .esrm-title {
        font-size: 20px;
        font-weight: 700;
        margin: 2px 0 8px;
        text-align: center;
    }
    .esrm-section {
        margin-bottom: 10px;
    }
    .esrm-subject {
        font-weight: 700;
        text-transform: uppercase;
    }
    .esrm-ticket-table {
        border-collapse: collapse;
        margin: 12px 0 8px;
        table-layout: fixed;
        width: 100%;
    }
    .esrm-ticket-table th,
    .esrm-ticket-table td {
        border: 1px solid #333;
        padding: 5px 6px;
        vertical-align: top;
        word-wrap: break-word;
    }
    .esrm-ticket-table th {
        background: #eef3f7;
        font-size: 10px;
        text-align: center;
        text-transform: uppercase;
    }
    .esrm-ticket-table .amount {
        text-align: right;
        white-space: nowrap;
    }
    .esrm-total-row td {
        font-weight: 700;
    }
    .esrm-amount-words {
        font-weight: 700;
        margin: 8px 0 14px;
        text-transform: capitalize;
    }
    .esrm-payment {
        margin-top: 12px;
        text-transform: uppercase;
    }
    .esrm-payment-lines {
        margin-top: 7px;
    }
    .esrm-signature {
        margin-top: 42px;
        text-transform: uppercase;
    }
    .esrm-signature-name {
        font-weight: 700;
    }
</style>

<div class="esrm-invoice">
    <div class="esrm-header">
        <img class="esrm-logo" src="/assets/esrm_travel/images/esrm-logo.svg">
        <div class="esrm-company">
            <h1>Ezzy Service and Resource Management Ltd</h1>
            <div class="esrm-company-address">{{ settings.invoice_letterhead_address or "" }}</div>
        </div>
    </div>

    <div class="esrm-meta">
        <div>
            <div><b>Client Name :</b> {{ doc.customer_name or doc.customer }}</div>
            <div><b>PURPOSE :</b> {{ tickets[0].purpose if tickets and tickets[0].purpose else "" }}</div>
            <div><b>REFFERENCE :</b> {{ tickets[0].reference if tickets and tickets[0].reference else (invoice_no.split("-")[0] if invoice_no else "") }}</div>
        </div>
        <table class="esrm-meta-table">
            <tr>
                <td><b>Invoice NO</b></td>
                <td>{{ invoice_no }}</td>
            </tr>
            <tr>
                <td><b>Date</b></td>
                <td>{{ frappe.utils.formatdate(doc.posting_date, "dd MMM yyyy") }}</td>
            </tr>
        </table>
    </div>

    <div class="esrm-title">INVOICE</div>

    <div class="esrm-section">
        <div>TO,</div>
        <div><b>{{ doc.customer_name or doc.customer }}</b></div>
        <div>{{ (doc.address_display or "") | safe }}</div>
    </div>

    <div class="esrm-section esrm-subject">SUBJECT : INVOICE FOR ISSUED AIR TICKET</div>
    <div class="esrm-section">DEAR SIR,</div>
    <div class="esrm-section">WE ARE PLEASED TO SUBMIT THE INVOICE AS</div>

    <table class="esrm-ticket-table">
        <thead>
            <tr>
                <th style="width: 4%;">SL</th>
                <th style="width: 11%;">IssueD</th>
                <th style="width: 22%;">PAX NAME</th>
                <th style="width: 15%;">TICKET NO</th>
                <th style="width: 14%;">ROUTE</th>
                <th style="width: 9%;">Carrier</th>
                <th style="width: 13%;">FARE(BDT)</th>
                <th style="width: 12%;">REMARKS</th>
            </tr>
        </thead>
        <tbody>
            {% for ticket in tickets %}
            <tr>
                <td style="text-align: center;">{{ loop.index }}</td>
                <td>{{ frappe.utils.formatdate(ticket.issue_date, "dd MMM yyyy") if ticket.issue_date else "" }}</td>
                <td>{{ ticket.passenger_name or "" }}</td>
                <td>{{ ticket.ticket_number or "" }}</td>
                <td>{{ ticket.route or "" }}</td>
                <td>{{ ticket.carrier or "" }}</td>
                <td class="amount">{{ frappe.utils.fmt_money(ticket.fare or 0, currency=doc.currency) }}</td>
                <td>{{ ticket.remarks or "" }}</td>
            </tr>
            {% endfor %}
            <tr class="esrm-total-row">
                <td colspan="6" class="amount">Total</td>
                <td class="amount">{{ frappe.utils.fmt_money(doc.grand_total or 0, currency=doc.currency) }}</td>
                <td></td>
            </tr>
        </tbody>
    </table>

    <div class="esrm-amount-words">{{ frappe.utils.money_in_words(doc.grand_total or 0, doc.currency) }}</div>

    <div class="esrm-payment">
        {{ settings.invoice_payment_instructions or "" }}
        <div class="esrm-payment-lines">
            <div><b>BANK ACCOUNT NUMBER :</b> {{ settings.invoice_bank_account_number or "" }}</div>
            <div><b>BANK NAME :</b> {{ settings.invoice_bank_name or "" }}</div>
            <div>{{ settings.invoice_bank_branch or "" }}</div>
        </div>
    </div>

    <div class="esrm-section" style="margin-top: 16px;">THANKING AND ASSURNING YOU THE BEST COOPERATION ALL TIME.</div>

    <div class="esrm-signature">
        <div>YOURS SINCERELY</div>
        <br><br>
        <div class="esrm-signature-name">{{ settings.invoice_signatory_name or "" }}</div>
        <div>{{ settings.invoice_signatory_designation or "" }}</div>
        <div>ESRM</div>
    </div>
</div>
"""
