import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt


class IATAMemo(Document):
    def autoname(self):
        self.naming_series = self.naming_series or "IATA-MEMO-.YYYY.-"
        self.name = make_autoname(self.naming_series)

    def before_validate(self):
        self.company = self.company or "Ezzy Services & Resource Management"
        self.memo_number = (self.memo_number or "").strip()
        if self.ticket_booking:
            booking = frappe.db.get_value(
                "Ticket Booking", self.ticket_booking,
                ["ticket_number", "travel_type", "payment_mode"], as_dict=True,
            )
            if not booking or booking.payment_mode != "IATA":
                frappe.throw(_("The related booking must be an IATA booking."))
            self.ticket_number = booking.ticket_number
            self.travel_type = booking.travel_type or self.travel_type

    def validate(self):
        if self.memo_type == "ACM" and flt(self.amount) >= 0:
            frappe.throw(_("ACM amounts must be negative because they reduce the IATA payable."))
        if self.memo_type == "ADM" and flt(self.amount) <= 0:
            frappe.throw(_("ADM amounts must be positive because they increase the IATA payable."))
        if self.memo_type == "Late Fee" and flt(self.amount) <= 0:
            frappe.throw(_("Late Fee amounts must be positive because they increase the IATA payable."))
        duplicate = frappe.db.get_value(
            "IATA Memo",
            {"memo_type": self.memo_type, "memo_number": self.memo_number, "name": ["!=", self.name]},
            "name",
        )
        if duplicate:
            frappe.throw(_("{0} {1} is already recorded as {2}.").format(self.memo_type, self.memo_number, duplicate))
        self.status = "Draft" if self.docstatus == 0 else self.status

    def on_submit(self):
        self.db_set("status", "Unsettled")

    def before_cancel(self):
        if self.iata_settlement and frappe.db.get_value("IATA Settlement", self.iata_settlement, "docstatus") == 1:
            frappe.throw(_("Cancel IATA Settlement {0} before cancelling this memo.").format(self.iata_settlement))

    def on_cancel(self):
        self.db_set({"status": "Cancelled", "iata_settlement": None})
