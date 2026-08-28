import base64
import hashlib
import json
from pathlib import Path

import frappe
from frappe.utils import flt


PRINT_FORMAT_NAME = "ESRM Ticket Invoice"
MONEY_RECEIPT_PRINT_FORMAT_NAME = "ESRM Money Receipt"
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
    return (
        ESRM_TICKET_INVOICE_HTML
        .replace("__ESRM_LOGO_DATA_URI__", get_image_data_uri("esrm-logo-print.png", "image/png"))
        .replace("__IATA_LOGO_DATA_URI__", get_image_data_uri("iata-accredited-agent-cropped.png", "image/png"))
        .replace("__ATAB_LOGO_DATA_URI__", get_image_data_uri("atab-logo.png", "image/png"))
    )


def get_money_receipt_html():
    return ESRM_MONEY_RECEIPT_HTML.replace(
        "__ESRM_LOGO_DATA_URI__", get_image_data_uri("esrm-logo-print.png", "image/png")
    )


def get_money_receipt_audit_code(payment_entry_name):
    payment = frappe.get_doc("Payment Entry", payment_entry_name)
    payload = {
        "name": payment.name,
        "docstatus": payment.docstatus,
        "posting_date": str(payment.posting_date),
        "party": payment.party,
        "received_amount": str(payment.received_amount or 0),
        "modified": str(payment.modified),
        "references": [
            [row.reference_doctype, row.reference_name, str(row.allocated_amount or 0)]
            for row in payment.references
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode()
    ).hexdigest().upper()


def get_image_data_uri(filename, mime_type):
    image_path = Path(frappe.get_app_path("esrm_travel", "public", "images", filename))
    if not image_path.exists():
        frappe.log_error(f"ESRM invoice image not found: {image_path}", "ESRM Invoice Print Format")
        return ""

    encoded_image = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded_image}"



def setup_print_formats():
    setup_esrm_ticket_invoice_print_format()
    setup_esrm_money_receipt_print_format()
    ensure_default_sales_invoice_print_format()
    ensure_default_money_receipt_print_format()
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


def setup_esrm_money_receipt_print_format():
    doc = get_or_create("Print Format", MONEY_RECEIPT_PRINT_FORMAT_NAME)
    doc.update(
        {
            "doc_type": "Payment Entry",
            "module": "ESRM Travel",
            "print_format_type": "Jinja",
            "custom_format": 1,
            "disabled": 0,
            "html": get_money_receipt_html(),
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


def ensure_default_money_receipt_print_format():
    if not frappe.db.exists("Print Format", MONEY_RECEIPT_PRINT_FORMAT_NAME):
        return

    current_default = frappe.get_meta("Payment Entry").default_print_format
    if current_default == MONEY_RECEIPT_PRINT_FORMAT_NAME:
        return

    existing_property_setter = frappe.db.exists(
        "Property Setter",
        {
            "doc_type": "Payment Entry",
            "doctype_or_field": "DocType",
            "property": "default_print_format",
        },
    )
    if existing_property_setter:
        frappe.db.set_value(
            "Property Setter",
            existing_property_setter,
            "value",
            MONEY_RECEIPT_PRINT_FORMAT_NAME,
        )
    else:
        frappe.make_property_setter(
            {
                "doctype": "Payment Entry",
                "doctype_or_field": "DocType",
                "property": "default_print_format",
                "value": MONEY_RECEIPT_PRINT_FORMAT_NAME,
                "property_type": "Data",
            },
            module="ESRM Travel",
        )

    frappe.clear_cache(doctype="Payment Entry")


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
        "invoice_bank_routing_number": "235260444",
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

def get_invoice_credit_summary(invoice_name):
    """Build customer-facing invoice rows including draft or posted adjustments."""
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    original_total = invoice.grand_total or 0
    credit_notes = frappe.get_all(
        "Sales Invoice",
        filters={
            "return_against": invoice_name,
            "is_return": 1,
            "docstatus": ["<", 2],
        },
        fields=["name", "grand_total", "docstatus"],
        order_by="posting_date asc, creation asc",
    )
    ticket_rows = []
    has_adjustments = False
    for row in invoice.get("esrm_ticket_bookings") or []:
        display_row = row.as_dict()
        booking = (
            frappe.db.get_value(
                "Ticket Booking",
                row.ticket_booking,
                [
                    "cancellation_status",
                    "invoice_amount",
                    "refund_amount",
                    "cancellation_fee",
                    "cancellation_date",
                ],
                as_dict=True,
            )
            if row.ticket_booking
            else None
        )
        if booking and booking.cancellation_status == "Draft Invoice Revised":
            has_adjustments = True
            display_row["fare"] = booking.invoice_amount
            ticket_rows.append(display_row)
            refund_row = dict(display_row)
            refund_row.update(
                {
                    "issue_date": booking.cancellation_date,
                    "fare": -flt(booking.refund_amount),
                    "remarks": "REFUND",
                }
            )
            ticket_rows.append(refund_row)
            if flt(booking.cancellation_fee):
                fee_row = dict(display_row)
                fee_row.update(
                    {
                        "issue_date": booking.cancellation_date,
                        "passenger_name": "",
                        "ticket_number": "",
                        "route": "",
                        "carrier": "",
                        "fare": flt(booking.cancellation_fee),
                        "remarks": "CANCELLATION FEE",
                    }
                )
                ticket_rows.append(fee_row)
        else:
            ticket_rows.append(display_row)

    revised_total = flt(original_total)
    for credit in credit_notes:
        has_adjustments = True
        credit_doc = frappe.get_doc("Sales Invoice", credit.name)
        revised_total += flt(credit.grand_total)
        for row in credit_doc.get("esrm_ticket_bookings") or []:
            ticket_rows.append(row.as_dict())
    return {
        "credit_notes": credit_notes,
        "tickets": ticket_rows,
        "revised_total": revised_total,
        "has_adjustments": has_adjustments,
    }


ESRM_TICKET_INVOICE_HTML = """
{% set settings = frappe.get_doc("ESRM Travel Settings") %}
{% set invoice_no = doc.esrm_invoice_number or doc.name %}
{% set is_credit_note = doc.is_return and doc.return_against %}
{% set tickets = doc.esrm_ticket_bookings or [] %}
{% set visa_services = doc.esrm_visa_services or [] %}
{% set general_services = doc.esrm_general_services or [] %}
{% set credit_summary = get_invoice_credit_summary(doc.name) if not is_credit_note else none %}
{% if credit_summary and credit_summary.tickets %}
    {% set tickets = credit_summary.tickets %}
{% endif %}
{% set company_name = "Ezzy Services & Resource Management" %}
{% set company_address = settings.invoice_letterhead_address if settings.invoice_letterhead_address and settings.invoice_letterhead_address != company_name else "" %}
{% set invoice_total = credit_summary.revised_total if credit_summary and credit_summary.has_adjustments else ((doc.grand_total or 0) if is_general_invoice else (doc.rounded_total or doc.grand_total or 0)) %}
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
{% if not visa_services and doc.esrm_visa_service %}
    {% set visa = frappe.get_doc("Visa Service", doc.esrm_visa_service) %}
    {% set visa_services = [{
        "application_date": visa.application_date,
        "applicant_name": visa.applicant_name,
        "passport_number": visa.passport_number,
        "country": visa.destination_country,
        "service_description": visa.destination_country ~ " - " ~ visa.visa_category ~ " - " ~ visa.visa_type,
        "amount": visa.invoice_amount,
        "remarks": visa.customer_remarks
    }] %}
{% endif %}
{% if not general_services and doc.esrm_general_service_order %}
    {% set general = frappe.get_doc("General Service Order", doc.esrm_general_service_order) %}
    {% set general_services = [{"general_service_order": general.name, "service_date": general.entry_date, "service_offering": general.service_offering, "subject": general.subject, "description": general.description, "quantity": 1, "amount": general.invoice_amount, "remarks": general.customer_remarks}] %}
{% endif %}
{% set is_visa_invoice = true if visa_services else false %}
{% set is_general_invoice = true if general_services else false %}
{% set general_order = frappe.get_doc("General Service Order", general_services[0].general_service_order) if is_general_invoice else none %}

<style>
    .esrm-invoice {
        color: #1f2933;
        font-family: Arial, sans-serif;
        font-size: 9pt;
        line-height: 1.25;
        min-height: 267mm;
        position: relative;
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
        line-height: 1.18;
        padding: 5px 4px;
        vertical-align: middle;
    }
    .esrm-ticket-table td {
        font-size: 7.5pt;
    }
    .esrm-ticket-table th {
        background: #eaf1f5;
        color: #243b53;
        font-size: 6.8pt;
        font-weight: 700;
        line-height: 1.1;
        text-align: center;
        white-space: nowrap;
    }
    .esrm-ticket-table .center {
        text-align: center !important;
        vertical-align: middle;
    }
    .esrm-ticket-table tbody td:nth-child(2),
    .esrm-ticket-table tbody td:nth-child(5),
    .esrm-ticket-table tbody td:nth-child(6) {
        text-align: center !important;
        vertical-align: middle;
    }
    .esrm-ticket-table .ticket-number {
        font-size: 7pt;
        letter-spacing: -0.1px;
        white-space: nowrap;
    }
    .esrm-ticket-table .route {
        font-size: 7.5pt;
        white-space: nowrap;
    }
    .esrm-ticket-table .amount {
        padding-left: 3px;
        padding-right: 5px;
        text-align: right;
        white-space: nowrap;
    }
    .esrm-ticket-table .passenger {
        overflow-wrap: anywhere;
        text-align: left;
    }
    .esrm-ticket-table .remarks {
        font-size: 7pt;
        line-height: 1.12;
        overflow-wrap: anywhere;
        text-align: left;
    }
    .esrm-visa-table th {
        font-size: 6.4pt;
        line-height: 1.08;
        white-space: normal;
    }
    .esrm-visa-table td {
        font-size: 7.1pt;
        overflow-wrap: anywhere;
        padding: 4px 3px;
    }
    .esrm-visa-table .ticket-number {
        font-size: 6.8pt;
        white-space: normal;
    }
    .esrm-visa-table .amount {
        font-size: 7pt;
        padding-left: 2px;
        padding-right: 3px;
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
        font-size: 8.3pt;
        line-height: 1.12;
        margin-top: 8px;
        padding: 6px 10px;
    }
    .esrm-payment-note {
        margin-bottom: 3px;
    }
    .esrm-payment-table {
        border-collapse: collapse;
        width: 100%;
    }
    .esrm-payment-table td {
        padding: 1px 0;
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
        vertical-align: bottom;
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
    .esrm-accreditation-logos {
        bottom: 0;
        position: absolute;
        right: 0;
        text-align: right;
        white-space: nowrap;
        z-index: 5;
    }
    .esrm-iata-logo {
        height: auto;
        margin-right: 8px;
        vertical-align: bottom;
        width: 122px;
    }
    .esrm-atab-logo {
        height: auto;
        vertical-align: bottom;
        width: 100px;
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
            <td><div class="esrm-title">{{ "Credit Note" if is_credit_note else ("Updated Invoice" if credit_summary and credit_summary.has_adjustments else "Invoice") }}</div></td>
            <td>
                <table class="esrm-meta-table">
                    <tr>
                        <td class="esrm-meta-label">Invoice No.</td>
                        <td>{{ invoice_no }}</td>
                    </tr>
                    <tr>
                        <td class="esrm-meta-label">Date</td>
                        <td>{{ frappe.utils.formatdate(general_order.entry_date if is_general_invoice and general_order else doc.posting_date, "dd MMM yyyy") }}</td>
                    </tr>
                    <tr>
                        <td class="esrm-meta-label">Currency</td>
                        <td>{{ doc.currency or "BDT" }}</td>
                    </tr>
                    {% if is_credit_note %}
                    <tr>
                        <td class="esrm-meta-label">Against Invoice</td>
                        <td>{{ doc.return_against }}</td>
                    </tr>
                    {% endif %}
                    {% if credit_summary and credit_summary.credit_notes %}
                    <tr>
                        <td class="esrm-meta-label">Credit Note</td>
                        <td>{{ credit_summary.credit_notes | map(attribute="name") | join(", ") }}</td>
                    </tr>
                    {% endif %}
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
                {% if is_general_invoice and general_order.attention_to %}<div style="margin-top:4px;"><strong>Attention:</strong> {{ general_order.attention_to }}</div>{% endif %}
            </td>
            <td class="esrm-summary">
                <div class="esrm-summary-block">
                    <div class="esrm-section-title">{{ ("Payroll Service Details" if general_order and general_order.print_profile == "Payroll" else "General Service Details") if is_general_invoice else ("Visa Service Details" if is_visa_invoice else "Booking Details") }}</div>
                    <table class="esrm-summary-table">
                        <tr>
                            <td class="esrm-summary-label">{{ "Subject:" if is_general_invoice else "Purpose:" }}</td>
                            <td>{{ general_services[0].subject if is_general_invoice else (visa_services[0].service_description if is_visa_invoice else (tickets[0].purpose if tickets and tickets[0].purpose else "")) }}</td>
                        </tr>
                        {% if not is_general_invoice or general_order.reference or general_order.client_reference or general_order.purchase_order %}<tr>
                            <td class="esrm-summary-label">Reference:</td>
                            <td>{{ (general_order.reference or general_order.client_reference or general_order.purchase_order) if is_general_invoice else (invoice_no.split("-")[0] if is_visa_invoice and invoice_no else (tickets[0].reference if tickets and tickets[0].reference else (invoice_no.split("-")[0] if invoice_no else ""))) }}</td>
                        </tr>
                        {% endif %}
                        {% if is_general_invoice and (general_order.service_period_from or general_order.service_period_to) %}<tr><td class="esrm-summary-label">Period:</td><td>{{ frappe.utils.formatdate(general_order.service_period_from, "dd MMM yyyy") if general_order.service_period_from else "" }}{% if general_order.service_period_to %} to {{ frappe.utils.formatdate(general_order.service_period_to, "dd MMM yyyy") }}{% endif %}</td></tr>{% endif %}
                    </table>
                </div>
            </td>
        </tr>
    </table>

    <div class="esrm-intro">{% if is_general_invoice and general_order.print_profile == "Payroll" %}We are pleased to submit the payroll service invoice for the period stated below:{% elif is_general_invoice %}We are pleased to submit the invoice for the following professional service(s):{% elif is_visa_invoice %}We are pleased to submit the invoice for the following visa assistance service(s):{% elif is_credit_note %}Credit for the following cancelled/refunded air ticket:{% else %}We are pleased to submit the invoice for the following issued air ticket(s):{% endif %}</div>

    <table class="esrm-ticket-table{% if is_visa_invoice %} esrm-visa-table{% endif %}">
        {% if is_general_invoice %}
        {% set invoice_charges = general_order.charges | selectattr("included_in_invoice") | list %}
        <colgroup><col style="width:6%;"><col style="width:69%;"><col style="width:25%;"></colgroup>
        <thead><tr><th>#</th><th>Description</th><th>Amount ({{ doc.currency or "BDT" }})</th></tr></thead>
        <tbody>
        {% for charge in invoice_charges %}
        <tr><td class="center">{{ loop.index }}</td><td>{{ charge.description or charge.charge_type }}</td><td class="amount">{{ "{:,.2f}".format(charge.amount or 0) }}</td></tr>
        {% endfor %}
        <tr class="esrm-total-row"><td colspan="2" class="amount">Total</td><td class="amount">{{ "{:,.2f}".format(invoice_total) }}</td></tr>
        </tbody>
        {% if general_order and general_order.applicants %}
        </table><div class="esrm-section-title">Applicant Annexure</div><table class="esrm-ticket-table esrm-visa-table">
        <thead><tr><th>#</th><th>Applicant</th><th>Nationality</th><th>Passport No.</th><th>Permit / Reference</th><th>Validity</th></tr></thead><tbody>
        {% for applicant in general_order.applicants %}<tr><td class="center">{{ loop.index }}</td><td>{{ applicant.applicant_name }}</td><td>{{ applicant.nationality or "" }}</td><td>{{ applicant.passport_number or "" }}</td><td>{{ applicant.permit_reference or "" }}</td><td>{{ frappe.utils.formatdate(applicant.expiry_date, "dd/MM/yyyy") if applicant.expiry_date else "" }}</td></tr>{% endfor %}
        </tbody>
        {% endif %}
        {% elif is_visa_invoice %}
        <colgroup>
            <col style="width: 4%;">
            <col style="width: 12%;">
            <col style="width: 20%;">
            <col style="width: 13%;">
            <col style="width: 11%;">
            <col style="width: 18%;">
            <col style="width: 14%;">
            <col style="width: 8%;">
        </colgroup>
        <thead>
            <tr>
                <th class="center">#</th>
                <th>Application Date</th>
                <th>Applicant</th>
                <th>Passport No.</th>
                <th>Destination</th>
                <th>Visa Service</th>
                <th class="center">Amount</th>
                <th>Remarks</th>
            </tr>
        </thead>
        <tbody>
            {% for visa in visa_services %}
            <tr>
                <td class="center">{{ loop.index }}</td>
                <td class="center">{{ frappe.utils.formatdate(visa.application_date, "dd/MM/yyyy") if visa.application_date else "" }}</td>
                <td class="passenger">{{ visa.applicant_name or "" }}</td>
                <td class="ticket-number">{{ visa.passport_number or "" }}</td>
                <td class="center">{{ visa.country or "" }}</td>
                <td>{{ (visa.service_description or "") | replace((visa.country or "") ~ " - ", "", 1) }}</td>
                <td class="amount">{{ doc.currency or "BDT" }} {{ "{:,.2f}".format(visa.amount or 0) }}</td>
                <td class="remarks">{{ visa.remarks or "" }}</td>
            </tr>
            {% endfor %}
            <tr class="esrm-total-row">
                <td colspan="6" class="amount">Total</td>
                <td class="amount">{{ doc.currency or "BDT" }} {{ "{:,.2f}".format(invoice_total) }}</td>
                <td></td>
            </tr>
        </tbody>
        {% else %}
        <colgroup>
            <col style="width: 4%;">
            <col style="width: 11%;">
            <col style="width: 20%;">
            <col style="width: 16%;">
            <col style="width: 11%;">
            <col style="width: 8%;">
            <col style="width: 15%;">
            <col style="width: 15%;">
        </colgroup>
        <thead>
            <tr>
                <th class="center">#</th>
                <th>Issue Date</th>
                <th>Passenger</th>
                <th>Ticket No.</th>
                <th>Route</th>
                <th>Airline</th>
                <th class="center">Amount</th>
                <th>Remarks</th>
            </tr>
        </thead>
        <tbody>
            {% for ticket in tickets %}
            <tr>
                <td class="center">{{ loop.index }}</td>
                <td class="center">{{ frappe.utils.formatdate(ticket.issue_date, "dd/MM/yyyy") if ticket.issue_date else "" }}</td>
                <td class="passenger">{{ ticket.passenger_name or "" }}</td>
                <td class="ticket-number">{{ ticket.ticket_number or "" }}</td>
                <td class="route center">{{ ticket.route or "" }}</td>
                <td class="center">{{ ticket.carrier or "" }}</td>
                <td class="amount">{{ doc.currency or "BDT" }} {{ "{:,.2f}".format(ticket.fare or 0) }}</td>
                <td class="remarks">{{ ticket.remarks or "" }}</td>
            </tr>
            {% endfor %}
            <tr class="esrm-total-row">
                <td colspan="6" class="amount">Total</td>
                <td class="amount">{{ doc.currency or "BDT" }} {{ "{:,.2f}".format(invoice_total) }}</td>
                <td></td>
            </tr>
        </tbody>
        {% endif %}
    </table>

    <div class="esrm-amount-words"><span class="esrm-amount-words-label">Amount in words:</span> <span class="esrm-amount-words-value">{{ frappe.utils.money_in_words(invoice_total, doc.currency) }}</span></div>

    {% if not is_credit_note %}
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
            <tr>
                <td class="esrm-payment-label">Routing Number</td>
                <td>{{ settings.invoice_bank_routing_number or "235260444" }}</td>
            </tr>
        </table>
    </div>
    {% endif %}

    <table class="esrm-footer-table">
        <tr>
            <td class="esrm-note">Thank you. We assure you of our best cooperation at all times.</td>
        </tr>
        <tr>
            <td class="esrm-signature">
                <div class="esrm-signature-line">
                    <div class="esrm-signature-name">{{ (general_order.signatory_name or settings.invoice_signatory_name or "") if is_general_invoice and general_order else (settings.invoice_signatory_name or "") }}</div>
                    <div>{{ (general_order.signatory_designation or settings.invoice_signatory_designation or "") if is_general_invoice and general_order else (settings.invoice_signatory_designation or "") }}</div>
                    <div>{{ company_name }}</div>
                </div>
            </td>
        </tr>
    </table>
    <div class="esrm-accreditation-logos">
        <img class="esrm-iata-logo" src="__IATA_LOGO_DATA_URI__">
        <img class="esrm-atab-logo" src="__ATAB_LOGO_DATA_URI__">
    </div>
</div>
"""


ESRM_MONEY_RECEIPT_HTML = """
{% set settings = frappe.get_doc("ESRM Travel Settings") %}
{% set receipt_amount = doc.received_amount if doc.payment_type == "Receive" else doc.paid_amount %}
{% set receipt_currency = doc.paid_to_account_currency if doc.payment_type == "Receive" else doc.paid_from_account_currency %}
{% set audit_code = get_money_receipt_audit_code(doc.name) %}
<style>
    @page { size: A4 portrait; margin: 12mm; }
    .mr-page { font-family: Arial, sans-serif; color: #1c2f3a; font-size: 10px; position: relative; min-height: 260mm; }
    .mr-watermark { position: fixed; top: 43%; left: 5%; width: 90%; text-align: center; font-size: 43px; font-weight: 700; letter-spacing: 3px; color: rgba(25, 79, 101, 0.07); z-index: -1; }
    .mr-header { border-bottom: 2px solid #174f68; padding: 0 0 10px; }
    .mr-logo { width: 145px; float: left; }
    .mr-company { text-align: right; line-height: 1.5; font-size: 10px; }
    .mr-company-name { font-size: 15px; color: #174f68; font-weight: 700; }
    .mr-title { margin: 18px 0 12px; text-align: center; color: #174f68; font-size: 23px; letter-spacing: 1px; }
    .mr-status { text-align: center; font-weight: 700; margin: -8px 0 12px; color: #a61e1e; }
    .mr-meta, .mr-details, .mr-allocations { width: 100%; border-collapse: collapse; }
    .mr-meta td, .mr-details td { border: 1px solid #aebbc3; padding: 7px 8px; }
    .mr-label { width: 19%; background: #e8f0f4; font-weight: 700; color: #244b5e; }
    .mr-details { margin-top: 12px; }
    .mr-section { margin: 16px 0 6px; color: #174f68; font-weight: 700; font-size: 11px; }
    .mr-allocations th, .mr-allocations td { border: 1px solid #aebbc3; padding: 6px; }
    .mr-allocations th { background: #e8f0f4; color: #244b5e; text-align: center; font-size: 9px; }
    .mr-number { text-align: right; white-space: nowrap; }
    .mr-center { text-align: center; }
    .mr-total td { background: #f2f5f7; font-weight: 700; }
    .mr-words { margin-top: 12px; border: 1px solid #aebbc3; padding: 9px; font-size: 11px; }
    .mr-remarks { margin-top: 10px; color: #43545e; }
    .mr-signature { margin-top: 36px; width: 42%; border-top: 1px solid #40545f; padding-top: 5px; line-height: 1.45; }
    .mr-signature-name { font-weight: 700; }
    .mr-audit { position: absolute; bottom: 0; width: 100%; border-top: 1px solid #b7c2c8; padding-top: 6px; color: #65757e; font-size: 7.5px; line-height: 1.45; }
    .mr-code { font-family: monospace; font-size: 7px; }
</style>

<div class="mr-page">
    <div class="mr-watermark">
        {% if doc.docstatus == 0 %}DRAFT · NOT VALID{% elif doc.docstatus == 2 %}CANCELLED{% else %}SYSTEM GENERATED RECEIPT{% endif %}
    </div>
    <div class="mr-header">
        <img class="mr-logo" src="__ESRM_LOGO_DATA_URI__">
        <div class="mr-company">
            <div class="mr-company-name">EZZY SERVICES &amp; RESOURCE MANAGEMENT</div>
            {{ settings.invoice_letterhead_address or "" }}
        </div>
        <div style="clear: both"></div>
    </div>

    <div class="mr-title">MONEY RECEIPT</div>
    {% if doc.docstatus != 1 %}<div class="mr-status">{{ "DRAFT — NOT A VALID RECEIPT" if doc.docstatus == 0 else "CANCELLED RECEIPT" }}</div>{% endif %}

    <table class="mr-meta">
        <tr><td class="mr-label">Receipt No.</td><td><strong>{{ doc.name }}</strong></td><td class="mr-label">Receipt Date</td><td>{{ frappe.utils.formatdate(doc.posting_date, "dd MMM yyyy") }}</td></tr>
        <tr><td class="mr-label">Received From</td><td><strong>{{ doc.party_name or doc.party or "" }}</strong></td><td class="mr-label">Payment Mode</td><td>{{ doc.mode_of_payment or "Not specified" }}</td></tr>
    </table>

    <table class="mr-details">
        <tr><td class="mr-label">Amount Received</td><td><strong>{{ frappe.utils.fmt_money(receipt_amount or 0, currency=receipt_currency or "BDT") }}</strong></td><td class="mr-label">Reference No.</td><td>{{ doc.reference_no or "—" }}</td></tr>
        <tr><td class="mr-label">Reference Date</td><td>{{ frappe.utils.formatdate(doc.reference_date, "dd MMM yyyy") if doc.reference_date else "—" }}</td><td class="mr-label">Deposit Account</td><td>{{ doc.paid_to if doc.payment_type == "Receive" else doc.paid_from }}</td></tr>
    </table>

    <div class="mr-words"><strong>Amount in words:</strong> {{ frappe.utils.money_in_words(receipt_amount or 0, receipt_currency or "BDT") }}</div>

    <div class="mr-section">INVOICE ALLOCATION</div>
    <table class="mr-allocations">
        <thead><tr><th style="width:5%">#</th><th style="width:18%">Document Type</th><th style="width:27%">Invoice / Reference</th><th style="width:16%">Invoice Total</th><th style="width:17%">Previous Outstanding</th><th style="width:17%">Amount Allocated</th></tr></thead>
        <tbody>
        {% for row in doc.references %}
        <tr>
            <td class="mr-center">{{ loop.index }}</td><td>{{ row.reference_doctype or "" }}</td><td>{{ row.reference_name or "" }}</td>
            <td class="mr-number">{{ frappe.utils.fmt_money(row.total_amount or 0, currency=receipt_currency or "BDT") }}</td>
            <td class="mr-number">{{ frappe.utils.fmt_money(row.outstanding_amount or 0, currency=receipt_currency or "BDT") }}</td>
            <td class="mr-number">{{ frappe.utils.fmt_money(row.allocated_amount or 0, currency=receipt_currency or "BDT") }}</td>
        </tr>
        {% else %}
        <tr><td colspan="6" class="mr-center">Payment received as an unallocated customer advance.</td></tr>
        {% endfor %}
        <tr class="mr-total"><td colspan="5" class="mr-number">TOTAL ALLOCATED</td><td class="mr-number">{{ frappe.utils.fmt_money(doc.total_allocated_amount or 0, currency=receipt_currency or "BDT") }}</td></tr>
        {% if doc.unallocated_amount %}<tr class="mr-total"><td colspan="5" class="mr-number">UNALLOCATED / ADVANCE</td><td class="mr-number">{{ frappe.utils.fmt_money(doc.unallocated_amount or 0, currency=receipt_currency or "BDT") }}</td></tr>{% endif %}
        </tbody>
    </table>

    {% if doc.remarks %}<div class="mr-remarks"><strong>Remarks:</strong> {{ doc.remarks }}</div>{% endif %}

    <div class="mr-signature">
        <div class="mr-signature-name">{{ settings.invoice_signatory_name or "" }}</div>
        <div>{{ settings.invoice_signatory_designation or "" }}</div>
        <div>Ezzy Services &amp; Resource Management</div>
    </div>

    <div class="mr-audit">
        This is a system-generated receipt based on Payment Entry {{ doc.name }}. It is valid only while the Payment Entry remains submitted.<br>
        Created by: {{ doc.owner }} &nbsp; | &nbsp; Last updated: {{ frappe.utils.format_datetime(doc.modified, "dd MMM yyyy, hh:mm a") }}<br>
        Audit code: <span class="mr-code">{{ audit_code }}</span>
    </div>
</div>
"""
