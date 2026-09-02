import re

import frappe
from frappe import _
from frappe.utils import flt


def _split_references(value):
    if isinstance(value, (list, tuple)):
        parts = value
    else:
        parts = re.split(r"[\n,;]+", value or "")

    references = []
    seen = set()
    for part in parts:
        reference = str(part).strip()
        key = reference.casefold()
        if reference and key not in seen:
            references.append(reference)
            seen.add(key)
    return references


@frappe.whitelist()
def get_outstanding_invoices_by_reference(party, references, company=None):
    """Resolve submitted outstanding invoices from ERP or customer invoice numbers."""
    if not frappe.has_permission("Payment Entry", ptype="create"):
        frappe.throw(_("You do not have permission to create Payment Entries."), frappe.PermissionError)
    if not party:
        frappe.throw(_("Select a customer first."))

    requested = _split_references(references)
    if not requested:
        frappe.throw(_("Enter at least one invoice reference."))

    filters = {
        "customer": party,
        "docstatus": 1,
        "outstanding_amount": [">", 0],
    }
    if company:
        filters["company"] = company

    invoices = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=[
            "name",
            "esrm_invoice_number",
            "posting_date",
            "due_date",
            "grand_total",
            "rounded_total",
            "outstanding_amount",
        ],
        order_by="posting_date asc, name asc",
        limit_page_length=0,
    )

    by_reference = {}
    for invoice in invoices:
        for value in (invoice.name, invoice.esrm_invoice_number):
            if value:
                by_reference.setdefault(str(value).strip().casefold(), []).append(invoice)

    matches = []
    missing = []
    ambiguous = []
    added = set()
    for reference in requested:
        candidates = by_reference.get(reference.casefold(), [])
        unique = {invoice.name: invoice for invoice in candidates}
        if not unique:
            missing.append(reference)
        elif len(unique) > 1:
            ambiguous.append({"reference": reference, "invoices": sorted(unique)})
        else:
            invoice = next(iter(unique.values()))
            if invoice.name not in added:
                matches.append(invoice)
                added.add(invoice.name)

    return {
        "invoices": matches,
        "missing": missing,
        "ambiguous": ambiguous,
        "total_outstanding": sum(flt(invoice.outstanding_amount) for invoice in matches),
    }
