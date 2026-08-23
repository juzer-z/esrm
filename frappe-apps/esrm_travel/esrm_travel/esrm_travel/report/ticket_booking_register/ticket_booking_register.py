import frappe
from frappe import _


ELEVATED_REPORT_ROLES = {"System Manager", "ESRM Approver"}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    data = get_data(filters)
    return get_columns(), data, None, get_chart(data), get_summary(data)


def get_columns():
    return [
        {"label": _("Service Type"), "fieldname": "service_type", "fieldtype": "Data", "width": 95},
        {"label": _("Record"), "fieldname": "name", "fieldtype": "Dynamic Link", "options": "service_doctype", "width": 155},
        {"label": _("Entry Date"), "fieldname": "entry_date", "fieldtype": "Date", "width": 100},
        {"label": _("Travel Date"), "fieldname": "travel_date", "fieldtype": "Date", "width": 100},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 170},
        {"label": _("Passenger / Applicant"), "fieldname": "traveller_name", "fieldtype": "Data", "width": 170},
        {"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 110},
        {"label": _("Airline"), "fieldname": "airline", "fieldtype": "Data", "width": 100},
        {"label": _("Ticket / Passport No."), "fieldname": "document_number", "fieldtype": "Data", "width": 145},
        {"label": _("Route"), "fieldname": "route_summary", "fieldtype": "Data", "width": 140},
        {"label": _("Destination"), "fieldname": "destination_country", "fieldtype": "Data", "width": 110},
        {"label": _("Visa Service"), "fieldname": "visa_service", "fieldtype": "Data", "width": 180},
        {"label": _("Invoice Number"), "fieldname": "invoice_number", "fieldtype": "Data", "width": 125},
        {"label": _("Owner"), "fieldname": "service_owner", "fieldtype": "Link", "options": "User", "width": 145},
        {"label": _("Approval"), "fieldname": "approval_status", "fieldtype": "Data", "width": 115},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 115},
        {"label": _("Invoice Status"), "fieldname": "invoice_status", "fieldtype": "Data", "width": 115},
        {"label": _("Payment Mode"), "fieldname": "payment_mode", "fieldtype": "Data", "width": 105},
        {"label": _("Gross Amount"), "fieldname": "gross_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Government Fee"), "fieldname": "government_fee", "fieldtype": "Currency", "width": 120},
        {"label": _("Service Charge"), "fieldname": "service_charge", "fieldtype": "Currency", "width": 115},
        {"label": _("Other Charges"), "fieldname": "other_charges", "fieldtype": "Currency", "width": 110},
        {"label": _("IATA Amount"), "fieldname": "iata_amount", "fieldtype": "Currency", "width": 115},
        {"label": _("Supplier Cost"), "fieldname": "supplier_cost", "fieldtype": "Currency", "width": 115},
        {"label": _("Invoice Amount"), "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Commission"), "fieldname": "commission", "fieldtype": "Currency", "width": 105},
        {"label": _("Discount"), "fieldname": "discount", "fieldtype": "Currency", "width": 100},
        {"label": _("Profit"), "fieldname": "profit", "fieldtype": "Currency", "width": 105},
        {"label": _("Paid Amount"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 115},
        {"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 115},
        {"label": _("Sales Invoice"), "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 145},
    ]


def get_data(filters):
    rows = []
    service_type = filters.get("service_type")
    if service_type in (None, "", "Ticket"):
        rows.extend(get_ticket_rows(filters))
    if service_type in (None, "", "Visa"):
        rows.extend(get_visa_rows(filters))
    return sorted(rows, key=lambda row: (row.entry_date or "", row.modified or ""), reverse=True)


def get_ticket_rows(filters):
    conditions, values = get_common_conditions(filters, "tb", "issue_date", "flight_date", "booking_owner")
    if filters.get("airline"):
        conditions.append("tb.airline = %(airline)s")
        values["airline"] = filters.airline
    if filters.get("payment_mode"):
        conditions.append("tb.payment_mode = %(payment_mode)s")
        values["payment_mode"] = filters.payment_mode
    if filters.get("destination_country"):
        return []
    if filters.get("search"):
        conditions.append(
            "(tb.ticket_number like %(search)s or tb.invoice_number like %(search)s "
            "or tb.customer like %(search)s or tb.passenger_name like %(search)s "
            "or tb.reference like %(search)s or tb.route_summary like %(search)s)"
        )
        values["search"] = f"%{filters.search}%"

    return frappe.db.sql(
        f"""
        select
            'Ticket' as service_type, 'Ticket Booking' as service_doctype,
            tb.name, tb.issue_date as entry_date, tb.flight_date as travel_date,
            tb.customer, tb.passenger_name as traveller_name, tb.reference,
            tb.airline, tb.ticket_number as document_number, tb.route_summary,
            '' as destination_country, '' as visa_service, tb.invoice_number,
            tb.booking_owner as service_owner, tb.approval_status, tb.status,
            tb.invoice_status, tb.payment_mode, tb.gross_amount,
            0 as government_fee, 0 as service_charge, 0 as other_charges,
            tb.iata_amount, tb.supplier_cost, tb.invoice_amount, tb.commission,
            tb.discount, tb.profit, tb.paid_amount, tb.outstanding_amount,
            tb.sales_invoice, tb.modified
        from `tabTicket Booking` tb
        where {" and ".join(conditions) if conditions else "1=1"}
        """,
        values,
        as_dict=True,
    )


def get_visa_rows(filters):
    conditions, values = get_common_conditions(
        filters, "vs", "application_date", "intended_travel_date", "service_owner"
    )
    if filters.get("airline") or filters.get("payment_mode"):
        return []
    if filters.get("destination_country"):
        conditions.append("vs.destination_country = %(destination_country)s")
        values["destination_country"] = filters.destination_country
    if filters.get("search"):
        conditions.append(
            "(vs.passport_number like %(search)s or vs.invoice_number like %(search)s "
            "or vs.customer like %(search)s or vs.applicant_name like %(search)s "
            "or vs.reference like %(search)s or vs.destination_country like %(search)s "
            "or vs.tracking_number like %(search)s)"
        )
        values["search"] = f"%{filters.search}%"

    return frappe.db.sql(
        f"""
        select
            'Visa' as service_type, 'Visa Service' as service_doctype,
            vs.name, vs.application_date as entry_date,
            vs.intended_travel_date as travel_date, vs.customer,
            vs.applicant_name as traveller_name, vs.reference, '' as airline,
            vs.passport_number as document_number, '' as route_summary,
            vs.destination_country,
            concat_ws(' - ', vs.visa_category, vs.visa_type, vs.processing_type) as visa_service,
            vs.invoice_number, vs.service_owner, vs.approval_status, vs.status,
            vs.invoice_status, '' as payment_mode,
            (ifnull(vs.government_fee, 0) + ifnull(vs.service_charge, 0) + ifnull(vs.other_charges, 0)) as gross_amount,
            vs.government_fee, vs.service_charge, vs.other_charges,
            0 as iata_amount, vs.supplier_cost, vs.invoice_amount,
            0 as commission, vs.discount, vs.profit, vs.paid_amount,
            vs.outstanding_amount, vs.sales_invoice, vs.modified
        from `tabVisa Service` vs
        where {" and ".join(conditions) if conditions else "1=1"}
        """,
        values,
        as_dict=True,
    )


def get_common_conditions(filters, alias, entry_date_field, travel_date_field, owner_field):
    conditions = []
    values = {}
    date_filters = (
        ("from_date", entry_date_field, ">="),
        ("to_date", entry_date_field, "<="),
        ("flight_from_date", travel_date_field, ">="),
        ("flight_to_date", travel_date_field, "<="),
    )
    for filter_name, fieldname, operator in date_filters:
        if filters.get(filter_name):
            conditions.append(f"{alias}.{fieldname} {operator} %({filter_name})s")
            values[filter_name] = filters.get(filter_name)
    for fieldname in ("customer", "reference", "approval_status", "status", "invoice_status"):
        if filters.get(fieldname):
            conditions.append(f"{alias}.{fieldname} = %({fieldname})s")
            values[fieldname] = filters.get(fieldname)
    if filters.get("booking_owner"):
        conditions.append(f"{alias}.{owner_field} = %(booking_owner)s")
        values["booking_owner"] = filters.booking_owner
    if not ELEVATED_REPORT_ROLES.intersection(frappe.get_roles()):
        conditions.append(f"{alias}.{owner_field} = %(current_user)s")
        values["current_user"] = frappe.session.user
    return conditions, values


def get_chart(data):
    if not data:
        return None
    counts = {"Ticket": 0, "Visa": 0}
    for row in data:
        counts[row.service_type] = counts.get(row.service_type, 0) + 1
    return {
        "data": {
            "labels": list(counts.keys()),
            "datasets": [{"name": _("Services"), "values": list(counts.values())}],
        },
        "type": "donut",
    }


def get_summary(data):
    if not data:
        return []
    tickets = sum(row.service_type == "Ticket" for row in data)
    visas = sum(row.service_type == "Visa" for row in data)
    return [
        {"label": _("Tickets"), "value": tickets, "datatype": "Int", "indicator": "Blue"},
        {"label": _("Visa Services"), "value": visas, "datatype": "Int", "indicator": "Purple"},
        {"label": _("IATA Amount"), "value": sum(row.iata_amount or 0 for row in data), "datatype": "Currency", "indicator": "Blue"},
        {"label": _("Invoice Amount"), "value": sum(row.invoice_amount or 0 for row in data), "datatype": "Currency", "indicator": "Green"},
        {"label": _("Collected"), "value": sum(row.paid_amount or 0 for row in data), "datatype": "Currency", "indicator": "Green"},
        {"label": _("Outstanding"), "value": sum(row.outstanding_amount or 0 for row in data), "datatype": "Currency", "indicator": "Orange"},
    ]
