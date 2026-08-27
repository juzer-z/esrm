import hashlib
import json

import frappe
from frappe import _
from frappe.utils import formatdate, get_datetime, getdate, now_datetime
from frappe.utils.pdf import get_pdf

from esrm_travel.print_formats import get_image_data_uri


def execute(filters=None):
    filters = validate_filters(filters)
    data = get_data(filters)
    return get_columns(), data, None, None, get_summary(data)


def validate_filters(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("Issue Date From and Issue Date To are required."))
    filters.from_date = getdate(filters.from_date)
    filters.to_date = getdate(filters.to_date)
    if filters.from_date > filters.to_date:
        frappe.throw(_("Issue Date From cannot be after Issue Date To."))
    return filters


def get_columns():
    return [
        {"label": _("Issue Date"), "fieldname": "issue_date", "fieldtype": "Date", "width": 100},
        {"label": _("Booking"), "fieldname": "name", "fieldtype": "Link", "options": "Ticket Booking", "width": 135},
        {"label": _("Passenger"), "fieldname": "passenger_name", "fieldtype": "Data", "width": 180},
        {"label": _("Ticket Number"), "fieldname": "ticket_number", "fieldtype": "Data", "width": 145},
        {"label": _("PNR"), "fieldname": "pnr", "fieldtype": "Data", "width": 90},
        {"label": _("Route"), "fieldname": "route_summary", "fieldtype": "Data", "width": 120},
        {"label": _("Airline"), "fieldname": "airline", "fieldtype": "Data", "width": 85},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": _("Gross Amount"), "fieldname": "gross_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Invoice Amount"), "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("IATA Amount"), "fieldname": "iata_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Payment Status"), "fieldname": "invoice_status", "fieldtype": "Data", "width": 115},
    ]


def get_data(filters):
    return frappe.db.sql(
        """
        select
            tb.name, tb.issue_date, tb.passenger_name, tb.ticket_number,
            tb.pnr, tb.route_summary, tb.airline, tb.customer,
            tb.gross_amount, tb.invoice_amount, tb.iata_amount,
            coalesce(si.status, tb.invoice_status, 'Not Invoiced') as invoice_status
        from `tabTicket Booking` tb
        left join `tabSales Invoice` si on si.name = tb.sales_invoice
        where tb.docstatus = 1
          and tb.approval_status = 'Approved'
          and tb.payment_mode = 'IATA'
          and tb.issue_date between %(from_date)s and %(to_date)s
        order by tb.issue_date, tb.name
        """,
        filters,
        as_dict=True,
    )


def get_summary(data):
    return [
        {"label": _("Approved IATA Bookings"), "value": len(data), "datatype": "Int", "indicator": "Blue"},
        {"label": _("Gross Amount"), "value": sum(row.gross_amount or 0 for row in data), "datatype": "Currency", "indicator": "Green"},
        {"label": _("Invoice Amount"), "value": sum(row.invoice_amount or 0 for row in data), "datatype": "Currency", "indicator": "Green"},
        {"label": _("IATA Amount"), "value": sum(row.iata_amount or 0 for row in data), "datatype": "Currency", "indicator": "Blue"},
    ]


def _verification_code(filters, data):
    payload = {
        "from_date": str(filters.from_date),
        "to_date": str(filters.to_date),
        "rows": [
            [
                row.name,
                str(row.issue_date),
                str(row.invoice_amount or 0),
                str(row.iata_amount or 0),
                row.invoice_status or "",
            ]
            for row in data
        ],
    }
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest().upper()


@frappe.whitelist()
def download_verified_pdf(from_date, to_date):
    if not frappe.has_permission("Ticket Booking", "read"):
        frappe.throw(_("You are not permitted to read Ticket Bookings."), frappe.PermissionError)

    filters = validate_filters({"from_date": from_date, "to_date": to_date})
    data = get_data(filters)
    generated_at = now_datetime()
    context = {
        "rows": data,
        "from_date": formatdate(filters.from_date, "dd MMM yyyy"),
        "to_date": formatdate(filters.to_date, "dd MMM yyyy"),
        "total_gross": sum(row.gross_amount or 0 for row in data),
        "total_invoice": sum(row.invoice_amount or 0 for row in data),
        "total_iata": sum(row.iata_amount or 0 for row in data),
        "generated_by": frappe.session.user,
        "generated_at": get_datetime(generated_at).strftime("%d %b %Y %I:%M %p"),
        "verification_code": _verification_code(filters, data),
        "logo": get_image_data_uri("esrm-logo-print.png", "image/png"),
    }
    html = frappe.render_template(
        "esrm_travel/templates/iata_payment_verification.html", context
    )
    pdf = get_pdf(html, options={"page-size": "A4", "orientation": "Landscape", "margin-top": "12mm", "margin-bottom": "12mm"})
    frappe.local.response.filename = f"IATA-Payment-Verification-{filters.from_date}-to-{filters.to_date}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "download"
    frappe.local.response.display_content_as = "attachment"
    frappe.local.response.content_type = "application/pdf"
