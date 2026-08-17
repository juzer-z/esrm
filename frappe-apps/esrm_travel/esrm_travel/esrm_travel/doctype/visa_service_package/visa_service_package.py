import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class VisaServicePackage(Document):
    def validate(self):
        for fieldname in (
            "government_fee",
            "service_charge",
            "other_charges",
            "default_supplier_cost",
            "expected_processing_days",
        ):
            if flt(self.get(fieldname)) < 0:
                frappe.throw(_("{0} cannot be negative.").format(self.meta.get_label(fieldname)))
        if self.effective_from and self.effective_until:
            if getdate(self.effective_until) < getdate(self.effective_from):
                frappe.throw(_("Effective Until cannot be before Effective From."))
