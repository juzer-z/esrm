import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, nowdate


class IATAAdjustment(Document):
    def autoname(self):
        self.naming_series = self.naming_series or "IATA-ADJ-.YYYY.-"
        self.name = make_autoname(self.naming_series)

    def before_validate(self):
        self.adjustment_date = self.adjustment_date or nowdate()
        self.status = "Draft" if self.docstatus == 0 else self.status
        if self.ticket_booking:
            booking = frappe.db.get_value(
                "Ticket Booking",
                self.ticket_booking,
                ["ticket_number", "passenger_name", "travel_type"],
                as_dict=True,
            )
            if booking:
                self.ticket_number = booking.ticket_number
                self.passenger_name = booking.passenger_name
                self.travel_type = booking.travel_type

    def validate(self):
        booking = frappe.db.get_value(
            "Ticket Booking",
            self.ticket_booking,
            ["docstatus", "approval_status", "payment_mode"],
            as_dict=True,
        )
        if not booking or booking.docstatus != 1 or booking.approval_status != "Approved":
            frappe.throw(_("Select an approved, submitted Ticket Booking."))
        if booking.payment_mode != "IATA":
            frappe.throw(_("IATA Adjustments can only be entered for IATA bookings."))
        amount = flt(self.adjustment_amount)
        if not amount:
            frappe.throw(_("Adjustment Amount cannot be zero."))
        if self.adjustment_type == "Credit / Refund" and amount >= 0:
            frappe.throw(_("Enter a negative amount for a credit or refund."))
        if self.adjustment_type == "Debit / Additional Charge" and amount <= 0:
            frappe.throw(_("Enter a positive amount for an additional charge."))

    def before_submit(self):
        if self.iata_settlement:
            frappe.throw(_("This adjustment is already linked to an IATA Settlement."))

    def on_submit(self):
        self.db_set("status", "Unsettled")

    def before_cancel(self):
        if self.iata_settlement:
            frappe.throw(
                _("Cancel IATA Settlement {0} before cancelling this adjustment.").format(
                    self.iata_settlement
                )
            )

    def on_cancel(self):
        self.db_set("status", "Cancelled")


@frappe.whitelist()
def create_submitted_adjustment(
    ticket_booking,
    adjustment_amount,
    adjustment_date=None,
    reference_no=None,
    remarks=None,
    attachment=None,
):
    booking_access = frappe.db.get_value(
        "Ticket Booking",
        ticket_booking,
        ["booking_owner", "cancellation_status"],
        as_dict=True,
    )
    can_submit = (
        frappe.session.user == "Administrator"
        or "ESRM Approver" in frappe.get_roles()
        or (
            booking_access
            and booking_access.booking_owner == frappe.session.user
            and booking_access.cancellation_status != "Active"
        )
    )
    if not can_submit:
        frappe.throw(
            _("Only the booking owner, Administrator, or an ESRM Approver can record this IATA credit."),
            frappe.PermissionError,
        )
    amount = flt(adjustment_amount)
    adjustment = frappe.get_doc(
        {
            "doctype": "IATA Adjustment",
            "ticket_booking": ticket_booking,
            "adjustment_date": adjustment_date or nowdate(),
            "adjustment_type": (
                "Credit / Refund" if amount < 0 else "Debit / Additional Charge"
            ),
            "adjustment_amount": amount,
            "reference_no": reference_no,
            "remarks": remarks,
            "attachment": attachment,
        }
    )
    adjustment.insert(ignore_permissions=True)
    adjustment.flags.ignore_permissions = True
    adjustment.submit()
    return adjustment.name
