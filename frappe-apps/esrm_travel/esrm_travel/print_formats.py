import base64
from pathlib import Path

import frappe


PRINT_FORMAT_NAME = "ESRM Ticket Invoice"
COMPANY_NAME = "Ezzy Services & Resource Management"
LEGACY_COMPANY_NAMES = (
    "Ezzy Service and Resource Management Ltd",
    "Ezzy Services and resources Management",
    "Ezzy Services & Resources Management",
)
LEGACY_PAYMENT_INSTRUCTIONS = (
    'WE ARE REQUESTING YOU TO PAY THE BILL AT YOUR EARLIEST. PLEASE NOTE THAT PAYMENT WILL BE MADE IN FAVOR OF "EZZY SERVICES & RESOURCE MANAGEMENT" BY ACCOUNT PAYEE CHEQUE/ DEPOSIT TO:',
)


def get_invoice_html():
    return ESRM_TICKET_INVOICE_HTML.replace("__ESRM_LOGO_DATA_URI__", get_logo_data_uri())


def get_logo_data_uri():
    logo_path = Path(frappe.get_app_path("esrm_travel", "public", "images", "esrm-logo-print.png"))
    if not logo_path.exists():
        frappe.log_error(f"ESRM logo source not found: {logo_path}", "ESRM Invoice Print Format")
        return ""

    encoded_logo = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded_logo}"



def setup_print_formats():
    setup_esrm_ticket_invoice_print_format()
    ensure_default_sales_invoice_print_format()
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
            "html": get_invoice_html(),
        }
    )
    save_doc(doc)


def ensure_default_sales_invoice_print_format():
    if not frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
        return

    current_default = frappe.get_meta("Sales Invoice").default_print_format
    if current_default == PRINT_FORMAT_NAME:
        return

    existing_property_setter = frappe.db.exists(
        "Property Setter",
        {
            "doc_type": "Sales Invoice",
            "doctype_or_field": "DocType",
            "property": "default_print_format",
        },
    )
    if existing_property_setter:
        frappe.db.set_value("Property Setter", existing_property_setter, "value", PRINT_FORMAT_NAME)
    else:
        frappe.make_property_setter(
            {
                "doctype": "Sales Invoice",
                "doctype_or_field": "DocType",
                "property": "default_print_format",
                "value": PRINT_FORMAT_NAME,
                "property_type": "Data",
            },
            module="ESRM Travel",
        )

    frappe.clear_cache(doctype="Sales Invoice")


def ensure_invoice_print_defaults():
    if not frappe.db.exists("DocType", "ESRM Travel Settings"):
        return

    settings = frappe.get_single("ESRM Travel Settings")
    defaults = {
        "invoice_letterhead_address": COMPANY_NAME,
        "invoice_payment_instructions": f"Please make payment in favor of {COMPANY_NAME} by account payee cheque or bank deposit.",
        "invoice_bank_account_number": "505-111-00000-199",
        "invoice_bank_name": "PREMIER BANK LTD.",
        "invoice_bank_branch": "BANANI SME BRANCH, DHAKA",
        "invoice_signatory_name": "U OAI MONG MARMA JOY",
        "invoice_signatory_designation": "ASSISTANT MANAGER",
    }

    changed = False
    for fieldname, value in defaults.items():
        current_value = settings.get(fieldname)
        if (
            not current_value
            or has_legacy_company_name(current_value)
            or (fieldname == "invoice_payment_instructions" and has_legacy_payment_instruction(current_value))
        ):
            settings.set(fieldname, value)
            changed = True

    if changed:
        settings.flags.ignore_mandatory = True
        settings.save(ignore_permissions=True)


def has_legacy_company_name(value):
    if not isinstance(value, str):
        return False

    normalized_value = value.lower()
    return any(legacy_name.lower() in normalized_value for legacy_name in LEGACY_COMPANY_NAMES)


def has_legacy_payment_instruction(value):
    if not isinstance(value, str):
        return False

    normalized_value = value.lower()
    return any(instruction.lower() == normalized_value for instruction in LEGACY_PAYMENT_INSTRUCTIONS)


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
{% set settings = frappe.get_doc("ESRM Travel Settings") %}
{% set invoice_no = doc.esrm_invoice_number or doc.name %}
{% set tickets = doc.esrm_ticket_bookings or [] %}
{% set company_name = "Ezzy Services & Resource Management" %}
{% set company_address = settings.invoice_letterhead_address if settings.invoice_letterhead_address and settings.invoice_letterhead_address != company_name else "" %}
{% set invoice_total = doc.rounded_total or doc.grand_total or 0 %}
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
        color: #1f2933;
        font-family: Arial, sans-serif;
        font-size: 10.5px;
        line-height: 1.45;
    }
    .esrm-header-table {
        border-bottom: 2px solid #24516a;
        margin-bottom: 18px;
        padding-bottom: 12px;
        width: 100%;
    }
    .esrm-logo-cell {
        vertical-align: top;
        width: 190px;
    }
    .esrm-logo {
        max-height: 76px;
        max-width: 170px;
        object-fit: contain;
    }
    .esrm-company-cell {
        text-align: right;
        vertical-align: top;
    }
    .esrm-company-name {
        color: #24516a;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 0;
        margin: 0 0 4px;
        text-transform: uppercase;
    }
    .esrm-company-address {
        color: #52616f;
        font-size: 10px;
        white-space: pre-line;
    }
    .esrm-title-row {
        margin: 8px 0 18px;
        width: 100%;
    }
    .esrm-title {
        color: #111827;
        font-size: 22px;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
    }
    .esrm-meta-table {
        border-collapse: collapse;
        margin-left: auto;
        width: 245px;
    }
    .esrm-meta-table td {
        border: 1px solid #d2d6dc;
        padding: 6px 8px;
    }
    .esrm-meta-label {
        background: #f3f6f8;
        color: #52616f;
        font-weight: 700;
        width: 96px;
    }
    .esrm-section-title {
        color: #24516a;
        font-size: 10px;
        font-weight: 700;
        margin-bottom: 4px;
        text-transform: uppercase;
    }
    .esrm-bill-table {
        margin-bottom: 16px;
        width: 100%;
    }
    .esrm-bill-to,
    .esrm-summary {
        vertical-align: top;
        width: 50%;
    }
    .esrm-customer-name {
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 3px;
    }
    .esrm-summary-line {
        margin-bottom: 3px;
    }
    .esrm-intro {
        margin: 10px 0 12px;
    }
    .esrm-ticket-table {
        border-collapse: collapse;
        margin: 10px 0 10px;
        table-layout: fixed;
        width: 100%;
    }
    .esrm-ticket-table th,
    .esrm-ticket-table td {
        border: 1px solid #c8d0d8;
        padding: 6px 6px;
        vertical-align: top;
        word-wrap: break-word;
    }
    .esrm-ticket-table th {
        background: #eaf1f5;
        color: #243b53;
        font-size: 9.5px;
        font-weight: 700;
        text-align: left;
        text-transform: uppercase;
    }
    .esrm-ticket-table .center {
        text-align: center;
    }
    .esrm-ticket-table .amount {
        text-align: right;
        white-space: nowrap;
    }
    .esrm-total-row td {
        background: #f7f9fb;
        font-weight: 700;
    }
    .esrm-amount-words {
        border: 1px solid #d2d6dc;
        margin: 10px 0 16px;
        padding: 8px 10px;
    }
    .esrm-amount-words span {
        font-weight: 700;
    }
    .esrm-payment-box {
        border: 1px solid #d2d6dc;
        margin-top: 14px;
        padding: 10px 12px;
    }
    .esrm-payment-note {
        margin-bottom: 8px;
    }
    .esrm-payment-table {
        border-collapse: collapse;
        width: 100%;
    }
    .esrm-payment-table td {
        padding: 3px 0;
        vertical-align: top;
    }
    .esrm-payment-table .label {
        color: #52616f;
        font-weight: 700;
        width: 135px;
    }
    .esrm-footer-table {
        margin-top: 34px;
        width: 100%;
    }
    .esrm-note {
        color: #52616f;
        font-size: 10px;
        vertical-align: bottom;
        width: 55%;
    }
    .esrm-signature {
        text-align: left;
        vertical-align: bottom;
        width: 45%;
    }
    .esrm-signature-line {
        border-top: 1px solid #111827;
        margin-top: 46px;
        padding-top: 6px;
        width: 230px;
    }
    .esrm-signature-name {
        font-weight: 700;
        text-transform: uppercase;
    }
</style>

<div class="esrm-invoice">
    <table class="esrm-header-table">
        <tr>
            <td class="esrm-logo-cell">
                <img class="esrm-logo" src="__ESRM_LOGO_DATA_URI__">
            </td>
            <td class="esrm-company-cell">
                <div class="esrm-company-name">{{ company_name }}</div>
                {% if company_address %}
                    <div class="esrm-company-address">{{ company_address }}</div>
                {% endif %}
            </td>
        </tr>
    </table>

    <table class="esrm-title-row">
        <tr>
            <td><div class="esrm-title">Invoice</div></td>
            <td>
                <table class="esrm-meta-table">
                    <tr>
                        <td class="esrm-meta-label">Invoice No.</td>
                        <td>{{ invoice_no }}</td>
                    </tr>
                    <tr>
                        <td class="esrm-meta-label">Date</td>
                        <td>{{ frappe.utils.formatdate(doc.posting_date, "dd MMM yyyy") }}</td>
                    </tr>
                    <tr>
                        <td class="esrm-meta-label">Currency</td>
                        <td>{{ doc.currency or "BDT" }}</td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>

    <table class="esrm-bill-table">
        <tr>
            <td class="esrm-bill-to">
                <div class="esrm-section-title">Bill To</div>
                <div class="esrm-customer-name">{{ doc.customer_name or doc.customer }}</div>
                <div>{{ (doc.address_display or "") | safe }}</div>
            </td>
            <td class="esrm-summary">
                <div class="esrm-section-title">Booking Details</div>
                <div class="esrm-summary-line"><b>Purpose:</b> {{ tickets[0].purpose if tickets and tickets[0].purpose else "" }}</div>
                <div class="esrm-summary-line"><b>Reference:</b> {{ tickets[0].reference if tickets and tickets[0].reference else (invoice_no.split("-")[0] if invoice_no else "") }}</div>
            </td>
        </tr>
    </table>

    <div class="esrm-intro">We are pleased to submit the invoice for the following issued air ticket(s):</div>

    <table class="esrm-ticket-table">
        <thead>
            <tr>
                <th style="width: 4%;" class="center">#</th>
                <th style="width: 11%;">Issue Date</th>
                <th style="width: 22%;">Passenger</th>
                <th style="width: 15%;">Ticket No.</th>
                <th style="width: 14%;">Route</th>
                <th style="width: 9%;">Airline</th>
                <th style="width: 13%;" class="amount">Amount</th>
                <th style="width: 12%;">Remarks</th>
            </tr>
        </thead>
        <tbody>
            {% for ticket in tickets %}
            <tr>
                <td class="center">{{ loop.index }}</td>
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
                <td class="amount">{{ frappe.utils.fmt_money(invoice_total, currency=doc.currency) }}</td>
                <td></td>
            </tr>
        </tbody>
    </table>

    <div class="esrm-amount-words"><span>Amount in words:</span> {{ frappe.utils.money_in_words(invoice_total, doc.currency) }}</div>

    <div class="esrm-payment-box">
        <div class="esrm-section-title">Payment Details</div>
        <div class="esrm-payment-note">{{ settings.invoice_payment_instructions or "Please make payment in favor of " ~ company_name ~ " by account payee cheque or bank deposit." }}</div>
        <table class="esrm-payment-table">
            <tr>
                <td class="label">Account Number</td>
                <td>{{ settings.invoice_bank_account_number or "" }}</td>
            </tr>
            <tr>
                <td class="label">Bank Name</td>
                <td>{{ settings.invoice_bank_name or "" }}</td>
            </tr>
            <tr>
                <td class="label">Branch</td>
                <td>{{ settings.invoice_bank_branch or "" }}</td>
            </tr>
        </table>
    </div>

    <table class="esrm-footer-table">
        <tr>
            <td class="esrm-note">Thank you. We assure you of our best cooperation at all times.</td>
            <td class="esrm-signature">
                <div class="esrm-signature-line">
                    <div>Authorized Signatory</div>
                    <div class="esrm-signature-name">{{ settings.invoice_signatory_name or "" }}</div>
                    <div>{{ settings.invoice_signatory_designation or "" }}</div>
                    <div>{{ company_name }}</div>
                </div>
            </td>
        </tr>
    </table>
</div>
"""