import base64
from pathlib import Path

import frappe


PRINT_FORMAT_NAME = "ESRM Ticket Invoice"
COMPANY_NAME = "Ezzy Services & Resource Management"
COMPANY_HEADER_DETAILS = "House 214, Road 13, New DOHS, Mohakhali, Dhaka - 1206. Email: esrmltd@ezzy.group"
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
        "invoice_letterhead_address": COMPANY_HEADER_DETAILS,
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
            or (fieldname == "invoice_letterhead_address" and current_value == COMPANY_NAME)
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
{% set customer_address = frappe.get_doc("Address", doc.customer_address) if doc.customer_address else none %}
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
        font-size: 9pt;
        line-height: 1.25;
    }
    .print-format .esrm-invoice {
        max-width: 185mm;
        margin: 0 auto;
    }
    .esrm-header-table {
        border-collapse: collapse;
        margin-bottom: 0;
        width: 100%;
    }
    .esrm-logo-cell {
        padding: 0 0 6pt;
        vertical-align: top;
        width: 232px;
    }
    .esrm-logo {
        display: block;
        height: auto;
        margin: -10pt 0 10pt;
        width: 146px;
    }
    .esrm-header-rule {
        border-top: 2px solid #24516a;
        height: 0;
        margin: 0 0 6px;
        width: 100%;
    }
    .esrm-company-cell {
        text-align: right;
        vertical-align: top;
    }
    .esrm-company-name {
        color: #24516a;
        font-size: 13pt;
        font-weight: 700;
        letter-spacing: 0;
        margin: 0 0 4px;
        text-transform: uppercase;
    }
    .esrm-company-address {
        color: #52616f;
        font-size: 7.5pt;
        line-height: 1.3;
        white-space: pre-line;
    }
    .esrm-title-row {
        margin: 6px 0 12px;
        width: 100%;
    }
    .esrm-title {
        color: #111827;
        font-size: 16pt;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
    }
    .esrm-meta-table {
        border-collapse: collapse;
        margin-left: auto;
        width: 255px;
    }
    .esrm-meta-table td {
        border: 1px solid #d2d6dc;
        padding: 4px 7px;
        vertical-align: middle;
    }
    .esrm-meta-label {
        background: #f3f6f8;
        color: #52616f;
        font-weight: 700;
        white-space: nowrap;
        width: 112px;
    }
    .esrm-section-title {
        color: #24516a;
        font-size: 8.5pt;
        font-weight: 700;
        margin-bottom: 4px;
        text-transform: uppercase;
    }
    .esrm-bill-table {
        margin-bottom: 6px;
        width: 100%;
    }
    .esrm-bill-to,
    .esrm-summary {
        vertical-align: top;
        width: 50%;
    }
    .esrm-customer-name {
        font-size: 9pt;
        font-weight: 700;
        margin-bottom: 3px;
    }
    .esrm-summary-block {
        margin-left: auto;
        width: 255px;
    }
    .esrm-summary-table {
        border-collapse: collapse;
        width: 100%;
    }
    .esrm-summary-table td {
        padding: 0 0 3px;
        vertical-align: top;
    }
    .esrm-summary-label {
        font-weight: 400;
        padding-right: 4px;
        white-space: nowrap;
        width: 66px;
    }
    .esrm-intro {
        margin: 6px 0 8px;
    }
    .esrm-ticket-table {
        border-collapse: collapse;
        margin: 7px 0 7px;
        table-layout: fixed;
        width: 100%;
    }
    .esrm-ticket-table th,
    .esrm-ticket-table td {
        border: 1px solid #c8d0d8;
        padding: 4px 5px;
        vertical-align: top;
        overflow-wrap: break-word;
    }
    .esrm-ticket-table td {
        font-size: 8pt;
    }
    .esrm-ticket-table th {
        background: #eaf1f5;
        color: #243b53;
        font-size: 7pt;
        font-weight: 700;
        text-align: center;
    }
    .esrm-ticket-table .center {
        text-align: center;
    }
    .esrm-ticket-table .ticket-number {
        font-size: 7.5pt;
        white-space: nowrap;
    }
    .esrm-ticket-table .route {
        font-size: 7.5pt;
        white-space: nowrap;
    }
    .esrm-ticket-table .amount {
        padding-left: 3px;
        padding-right: 7px;
        text-align: right;
        white-space: nowrap;
    }
    .esrm-total-row td {
        background: #f7f9fb;
        font-weight: 700;
    }
    .esrm-amount-words {
        border: 1px solid #d2d6dc;
        margin: 7px 0 10px;
        padding: 6px 8px;
    }
    .esrm-amount-words-label {
        font-weight: 400;
    }
    .esrm-amount-words-value {
        font-weight: 700;
    }
    .esrm-payment-box {
        border: 1px solid #d2d6dc;
        margin-top: 8px;
        padding: 7px 10px;
    }
    .esrm-payment-note {
        margin-bottom: 5px;
    }
    .esrm-payment-table {
        border-collapse: collapse;
        width: 100%;
    }
    .esrm-payment-table td {
        padding: 2px 0;
        vertical-align: top;
    }
    .esrm-payment-label {
        color: #52616f;
        font-weight: 700;
        width: 160px;
    }
    .esrm-footer-table {
        margin-top: 18px;
        width: 100%;
    }
    .esrm-note {
        color: #52616f;
        font-size: 8.5pt;
        padding-bottom: 10px;
        text-align: left;
        width: 100%;
    }
    .esrm-signature {
        text-align: left;
        width: 100%;
    }
    .esrm-signature-line {
        margin-top: 26px;
        width: 260px;
        white-space: nowrap;
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
                    <div class="esrm-company-address">{{ company_address | replace(" Email:", "\nEmail:") }}</div>
                {% endif %}
            </td>
        </tr>
    </table>
    <div class="esrm-header-rule"></div>

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
                {% if customer_address %}
                    {% if customer_address.address_line1 %}<div>{{ customer_address.address_line1 }}</div>{% endif %}
                    {% if customer_address.address_line2 %}<div>{{ customer_address.address_line2 }}</div>{% endif %}
                    <div>{{ customer_address.city or "" }}{% if customer_address.pincode %} {{ customer_address.pincode }}{% endif %}{% if customer_address.country %}{% if customer_address.city or customer_address.pincode %}, {% endif %}{{ customer_address.country }}{% endif %}</div>
                {% else %}
                    <div>{{ (doc.address_display or "") | safe }}</div>
                {% endif %}
            </td>
            <td class="esrm-summary">
                <div class="esrm-summary-block">
                    <div class="esrm-section-title">Booking Details</div>
                    <table class="esrm-summary-table">
                        <tr>
                            <td class="esrm-summary-label">Purpose:</td>
                            <td>{{ tickets[0].purpose if tickets and tickets[0].purpose else "" }}</td>
                        </tr>
                        <tr>
                            <td class="esrm-summary-label">Reference:</td>
                            <td>{{ tickets[0].reference if tickets and tickets[0].reference else (invoice_no.split("-")[0] if invoice_no else "") }}</td>
                        </tr>
                    </table>
                </div>
            </td>
        </tr>
    </table>

    <div class="esrm-intro">We are pleased to submit the invoice for the following issued air ticket(s):</div>

    <table class="esrm-ticket-table">
        <thead>
            <tr>
                <th style="width: 4%;" class="center">#</th>
                <th style="width: 11%;">Issue Date</th>
                <th style="width: 19%;">Passenger</th>
                <th style="width: 15%;">Ticket No.</th>
                <th style="width: 12%;">Route</th>
                <th style="width: 9%;">Airline</th>
                <th style="width: 19%;" class="center">Amount</th>
                <th style="width: 11%;">Remarks</th>
            </tr>
        </thead>
        <tbody>
            {% for ticket in tickets %}
            <tr>
                <td class="center">{{ loop.index }}</td>
                <td>{{ frappe.utils.formatdate(ticket.issue_date, "dd/MM/yyyy") if ticket.issue_date else "" }}</td>
                <td>{{ ticket.passenger_name or "" }}</td>
                <td class="ticket-number">{{ ticket.ticket_number or "" }}</td>
                <td class="route">{{ ticket.route or "" }}</td>
                <td>{{ ticket.carrier or "" }}</td>
                <td class="amount">{{ doc.currency or "BDT" }} {{ "{:,.2f}".format(ticket.fare or 0) }}</td>
                <td>{{ ticket.remarks or "" }}</td>
            </tr>
            {% endfor %}
            <tr class="esrm-total-row">
                <td colspan="6" class="amount">Total</td>
                <td class="amount">{{ doc.currency or "BDT" }} {{ "{:,.2f}".format(invoice_total) }}</td>
                <td></td>
            </tr>
        </tbody>
    </table>

    <div class="esrm-amount-words"><span class="esrm-amount-words-label">Amount in words:</span> <span class="esrm-amount-words-value">{{ frappe.utils.money_in_words(invoice_total, doc.currency) }}</span></div>

    <div class="esrm-payment-box">
        <div class="esrm-section-title">Payment Details</div>
        <div class="esrm-payment-note">{{ (settings.invoice_payment_instructions or "Please make payment in favor of " ~ company_name ~ " by account payee cheque or bank deposit.") | replace(company_name, "<strong>" ~ company_name ~ "</strong>") | safe }}</div>
        <table class="esrm-payment-table">
            <tr>
                <td class="esrm-payment-label">Account No.</td>
                <td>{{ settings.invoice_bank_account_number or "" }}</td>
            </tr>
            <tr>
                <td class="esrm-payment-label">Bank Name</td>
                <td>{{ settings.invoice_bank_name or "" }}</td>
            </tr>
            <tr>
                <td class="esrm-payment-label">Branch</td>
                <td>{{ settings.invoice_bank_branch or "" }}</td>
            </tr>
        </table>
    </div>

    <table class="esrm-footer-table">
        <tr>
            <td class="esrm-note">Thank you. We assure you of our best cooperation at all times.</td>
        </tr>
        <tr>
            <td class="esrm-signature">
                <div class="esrm-signature-line">
                    <div class="esrm-signature-name">{{ settings.invoice_signatory_name or "" }}</div>
                    <div>{{ settings.invoice_signatory_designation or "" }}</div>
                    <div>{{ company_name }}</div>
                </div>
            </td>
        </tr>
    </table>
</div>
"""
