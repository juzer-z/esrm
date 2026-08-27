import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, now, nowdate


AMENDMENT_AUDIT_FIELDS = {
    "amendment_reason",
    "last_amended_by",
    "last_amended_at",
    "amendment_count",
}
AUTOMATIC_AFTER_SUBMIT_FIELDS = {
    "route_summary",
    "status",
    "invoice_status",
    "cost_status",
    "cost_entered_by_owner",
    "commission",
    "discount",
    "profit",
    "paid_amount",
    "outstanding_amount",
    "sales_invoice",
    "cancellation_status",
    "cancellation_date",
    "cancellation_reason",
    "refund_amount",
    "cancellation_fee",
    "net_credit_amount",
    "revised_invoice_amount",
    "credit_note",
}
INVOICE_BOUND_FIELDS = {
    "customer",
    "reference",
    "invoice_number",
    "issue_date",
    "passenger_name",
    "purpose",
    "pnr",
    "ticket_number",
    "airline",
    "flight_date",
    "return_date",
    "flight_number",
    "travel_type",
    "trip_type",
    "sectors",
    "gross_amount",
    "invoice_amount",
    "remarks",
}


class TicketBooking(Document):
    def autoname(self):
        settings_series = None
        if frappe.db.exists("DocType", "ESRM Travel Settings"):
            settings_series = frappe.db.get_single_value("ESRM Travel Settings", "ticket_booking_series")

        series = settings_series or self.naming_series or "TB-.YYYY.-"
        self.naming_series = series
        self.name = make_autoname(series)

    def before_validate(self):
        if self.is_new() and (frappe.session.user != "Administrator" or not self.booking_owner):
            self.booking_owner = frappe.session.user
        elif not self.is_new() and frappe.session.user != "Administrator":
            self.booking_owner = frappe.db.get_value("Ticket Booking", self.name, "booking_owner") or frappe.session.user
        if not self.approval_status:
            self.approval_status = "Draft"
        if not self.invoice_number:
            self.invoice_number = self.get_next_invoice_number()

    def validate(self):
        self.validate_travel_dates()
        self.validate_amounts()
        self.set_cost_completion()
        self.calculate_profitability()
        self.validate_invoice_number()
        self.set_route_summary()
        self.sync_invoice_details()
        self.set_status()

    def before_update_after_submit(self):
        if frappe.session.user == "Administrator":
            self.validate_administrator_amendment()
        else:
            self.validate_booking_owner_cost_update()
        self.validate_travel_dates()
        self.validate_amounts()
        self.set_cost_completion()
        self.calculate_profitability()

    def validate_travel_dates(self):
        if self.trip_type == "Return":
            if not self.return_date:
                frappe.throw(_("Return Date is required for a return trip."))
            if self.flight_date and getdate(self.return_date) < getdate(self.flight_date):
                frappe.throw(_("Return Date cannot be before Flight Date."))
        else:
            self.return_date = None

    def on_submit(self):
        self.create_sales_invoice_on_approval()

    def create_sales_invoice_on_approval(self):
        """Atomically create, submit, and link the invoice on booking approval."""
        if self.approval_status != "Approved" or self.sales_invoice:
            return

        try:
            invoice_name = make_and_submit_sales_invoice([self.name])
        except Exception as exc:
            frappe.log_error(
                title=f"Automatic invoice creation failed for {self.name}",
                message=frappe.get_traceback(),
            )
            frappe.throw(
                _(
                    "Ticket Booking {0} could not be approved because its Sales Invoice "
                    "could not be created. Correct the invoice setup or booking values and try again. "
                    "Reason: {1}"
                ).format(self.name, str(exc))
            )

        self.sales_invoice = invoice_name
        self.invoice_status = frappe.db.get_value(
            "Sales Invoice", invoice_name, "status"
        ) or "Unpaid"
        self.status = "Invoiced"
        self.add_comment(
            "Info",
            _("Sales Invoice {0} was created and submitted automatically on approval.").format(
                invoice_name
            ),
        )

    def on_update_after_submit(self):
        if getattr(self, "_administrator_amendment_fields", None):
            labels = [
                self.meta.get_label(fieldname) or fieldname
                for fieldname in self._administrator_amendment_fields
            ]
            self.add_comment(
                "Edit",
                _(
                    "Administrator amended approved booking fields: {0}. Reason: {1}"
                ).format(", ".join(labels), self.amendment_reason),
            )
        if getattr(self, "_replace_linked_invoice", None):
            self.replace_linked_sales_invoice()
        elif getattr(self, "_sync_linked_draft_invoice", False):
            self.sync_linked_draft_sales_invoice()
        elif (
            getattr(self, "_administrator_amendment_fields", None)
            and not self.sales_invoice
        ):
            self.create_corrected_invoice_after_unlinked_amendment()

    def validate_administrator_amendment(self):
        if self.approval_status != "Approved":
            return

        previous = self.get_doc_before_save()
        if not previous:
            frappe.throw(_("Unable to verify the previous booking values."))

        changed_fields = {
            field.fieldname
            for field in self.meta.fields
            if field.fieldtype
            not in {"Section Break", "Column Break", "Tab Break", "HTML", "Button"}
            and self.has_value_changed(field.fieldname)
        }
        substantive_changes = sorted(
            changed_fields - AMENDMENT_AUDIT_FIELDS - AUTOMATIC_AFTER_SUBMIT_FIELDS
        )
        if not substantive_changes:
            return

        reason = (self.amendment_reason or "").strip()
        if not reason or not self.has_value_changed("amendment_reason"):
            frappe.throw(
                _(
                    "Enter a new Amendment Reason before saving changes to an approved booking."
                )
            )

        invoice_changes = sorted(set(substantive_changes) & INVOICE_BOUND_FIELDS)
        if self.sales_invoice and invoice_changes:
            invoice_status = frappe.db.get_value(
                "Sales Invoice",
                self.sales_invoice,
                ["docstatus", "status"],
                as_dict=True,
            )
            if not invoice_status:
                frappe.throw(
                    _("Linked Sales Invoice {0} no longer exists.").format(
                        self.sales_invoice
                    )
                )
            if invoice_status.docstatus == 0:
                self._sync_linked_draft_invoice = True
            else:
                self._replace_linked_invoice = self.sales_invoice

        self.amendment_reason = reason
        self.last_amended_by = frappe.session.user
        self.last_amended_at = now()
        self.amendment_count = (previous.amendment_count or 0) + 1
        self._administrator_amendment_fields = substantive_changes

    def replace_linked_sales_invoice(self):
        """Replace the linked invoice after an Administrator booking amendment."""
        previous_invoice_name = self._replace_linked_invoice
        previous_invoice = frappe.get_doc("Sales Invoice", previous_invoice_name)
        previous_docstatus = previous_invoice.docstatus

        if previous_invoice.docstatus == 1:
            from esrm_travel.workflow import cancel_sales_invoice

            cancel_sales_invoice(previous_invoice_name)
        elif previous_invoice.docstatus == 0:
            previous_invoice.flags.ignore_permissions = True
            previous_invoice.delete()
        else:
            from esrm_travel.workflow import sync_ticket_booking

            sync_ticket_booking(
                self.name,
                sales_invoice_name=previous_invoice_name,
                clear_sales_invoice=True,
            )

        new_invoice_name = make_and_submit_sales_invoice(
            [self.name],
            amended_from=(
                previous_invoice_name if previous_docstatus in {1, 2} else None
            ),
        )
        self.sales_invoice = new_invoice_name
        self.add_comment(
            "Info",
            _(
                "Sales Invoice {0} replaced {1} automatically after the booking amendment."
            ).format(new_invoice_name, previous_invoice_name),
        )

    def create_corrected_invoice_after_unlinked_amendment(self):
        """Create a submitted correction after the prior invoice was cancelled manually."""
        previous_invoice_name = frappe.db.sql(
            """
            select invoice.name
            from `tabSales Invoice` invoice
            inner join `tabESRM Invoice Ticket` ticket
                on ticket.parent = invoice.name
                and ticket.parenttype = 'Sales Invoice'
            where ticket.ticket_booking = %s
                and invoice.docstatus = 2
                and ifnull(invoice.is_return, 0) = 0
            order by invoice.modified desc
            limit 1
            """,
            self.name,
        )
        amended_from = previous_invoice_name[0][0] if previous_invoice_name else None
        new_invoice_name = make_and_submit_sales_invoice(
            [self.name], amended_from=amended_from
        )
        self.sales_invoice = new_invoice_name
        self.add_comment(
            "Info",
            _(
                "Corrected Sales Invoice {0} was created and submitted automatically "
                "after the booking amendment."
            ).format(new_invoice_name),
        )

    def sync_linked_draft_sales_invoice(self):
        invoice = frappe.get_doc("Sales Invoice", self.sales_invoice)
        if invoice.docstatus != 0:
            frappe.throw(
                _("Only a draft Sales Invoice can be synchronized automatically.")
            )

        ticket_rows = list(invoice.get("esrm_ticket_bookings") or [])
        current_row = next(
            (row for row in ticket_rows if row.ticket_booking == self.name),
            None,
        )
        if not current_row:
            frappe.throw(
                _(
                    "Sales Invoice {0} does not contain a ticket row for Booking {1}."
                ).format(invoice.name, self.name)
            )

        bookings = []
        for row in ticket_rows:
            booking = (
                self
                if row.ticket_booking == self.name
                else frappe.get_doc("Ticket Booking", row.ticket_booking)
            )
            bookings.append(booking)

        other_customers = {
            booking.customer
            for booking in bookings
            if booking.name != self.name and booking.customer
        }
        if other_customers and (
            len(other_customers) > 1 or self.customer not in other_customers
        ):
            frappe.throw(
                _(
                    "Customer cannot be changed because Sales Invoice {0} also contains bookings for another customer."
                ).format(invoice.name)
            )

        rate = flt(self.invoice_amount) or flt(self.gross_amount)
        if rate <= 0:
            frappe.throw(
                _("Invoice Amount or Gross Amount must be greater than zero.")
            )

        current_row.update(build_invoice_ticket_row(self, rate))

        item = next(
            (row for row in invoice.items if row.idx == current_row.idx),
            None,
        )
        if not item:
            frappe.throw(
                _(
                    "Sales Invoice {0} does not contain the matching item row for Booking {1}."
                ).format(invoice.name, self.name)
            )

        settings = frappe.get_single("ESRM Travel Settings")
        item.rate = rate
        item.description = build_invoice_description(self)
        item.income_account = get_booking_income_account(self, settings)

        customer_name = (
            frappe.db.get_value("Customer", self.customer, "customer_name")
            or self.customer
        )
        invoice.customer = self.customer
        invoice.customer_name = customer_name
        invoice.title = customer_name
        invoice.esrm_invoice_number = bookings[0].invoice_number
        invoice.esrm_ticket_booking = bookings[0].name
        invoice_due_date = get_invoice_due_date(bookings, invoice.posting_date)
        invoice.due_date = invoice_due_date
        for payment in invoice.get("payment_schedule") or []:
            if not payment.due_date or getdate(payment.due_date) < invoice_due_date:
                payment.due_date = invoice_due_date
        invoice.remarks = "\n\n".join(
            build_invoice_description(booking) for booking in bookings
        )
        invoice.flags.ignore_permissions = True
        invoice.save()
        self.add_comment(
            "Edit",
            _("Linked draft Sales Invoice {0} was synchronized.").format(
                invoice.name
            ),
        )

    def validate_booking_owner_cost_update(self):
        if frappe.session.user != self.booking_owner:
            frappe.throw(
                _("Only the booking owner or Administrator can update an approved booking."),
                frappe.PermissionError,
            )

        if self.approval_status != "Approved":
            frappe.throw(
                _("The booking owner can enter cost only after the booking is approved."),
                frappe.PermissionError,
            )

        previous = self.get_doc_before_save()
        if not previous:
            frappe.throw(_("Unable to verify the previous booking values."))

        cost_field = "iata_amount" if previous.payment_mode == "IATA" else "supplier_cost"
        if flt(self.get(cost_field)) <= 0:
            frappe.throw(
                _("{0} must be greater than zero.").format(
                    self.meta.get_label(cost_field)
                )
            )

        allowed_changes = {
            cost_field,
            "cost_entered_by_owner",
            "cost_status",
            "commission",
            "discount",
            "profit",
            "route_summary",
            "status",
            "invoice_status",
            "invoice_amount",
            "paid_amount",
            "outstanding_amount",
        }
        restricted_changes = [
            field.fieldname
            for field in self.meta.fields
            if field.allow_on_submit
            and field.fieldname not in allowed_changes
            and (
                self.child_table_has_changed(previous, field)
                if field.fieldtype == "Table"
                else self.has_value_changed(field.fieldname)
            )
        ]
        if restricted_changes:
            frappe.throw(
                _("After approval, you can only update the booking cost."),
                frappe.PermissionError,
            )

        self.cost_entered_by_owner = 1

    def child_table_has_changed(self, previous, table_field):
        child_meta = frappe.get_meta(table_field.options)
        value_fields = [
            field.fieldname
            for field in child_meta.fields
            if field.fieldtype
            not in {"Section Break", "Column Break", "Tab Break", "HTML", "Button"}
        ]

        def comparable_rows(rows):
            return [
                tuple(row.get(fieldname) for fieldname in value_fields)
                for row in (rows or [])
            ]

        return comparable_rows(self.get(table_field.fieldname)) != comparable_rows(
            previous.get(table_field.fieldname)
        )

    def validate_amounts(self):
        amount_fields = [
            "gross_amount",
            "iata_amount",
            "supplier_cost",
            "invoice_amount",
            "paid_amount",
            "outstanding_amount",
        ]
        for fieldname in amount_fields:
            value = flt(self.get(fieldname))
            if value < 0:
                frappe.throw(_("{0} cannot be negative.").format(self.meta.get_label(fieldname)))

        if flt(self.paid_amount) > flt(self.invoice_amount) and flt(self.invoice_amount) > 0:
            frappe.throw(_("Paid Amount cannot be greater than Invoice Amount."))

    def calculate_profitability(self):
        gross_amount = flt(self.gross_amount)
        iata_amount = flt(self.iata_amount)
        supplier_cost = flt(self.supplier_cost)
        invoice_amount = flt(self.invoice_amount)

        if self.payment_mode == "IATA":
            self.commission = gross_amount - iata_amount
            self.profit = invoice_amount - iata_amount if iata_amount > 0 else 0
        else:
            self.commission = 0
            self.profit = invoice_amount - supplier_cost if supplier_cost > 0 else 0

        self.discount = gross_amount - invoice_amount

    def set_cost_completion(self):
        if self.payment_mode == "IATA":
            self.cost_status = (
                "Incomplete" if flt(self.iata_amount) <= 0 else "Complete"
            )
        else:
            self.cost_status = (
                "Incomplete" if flt(self.supplier_cost) <= 0 else "Complete"
            )

    def validate_invoice_number(self):
        if not self.invoice_number:
            return

        duplicate = frappe.db.exists(
            "Ticket Booking",
            {
                "invoice_number": self.invoice_number,
                "name": ["!=", self.name],
            },
        )
        if duplicate:
            frappe.throw(_("Invoice Number {0} is already used in Ticket Booking {1}.").format(self.invoice_number, duplicate))

    def get_next_invoice_number(self):
        prefix = self.get_invoice_prefix()
        existing_numbers = frappe.db.sql(
            """
            select invoice_number
            from `tabTicket Booking`
            where invoice_number like %(invoice_prefix)s
              and name != %(name)s
            """,
            {"invoice_prefix": f"{prefix}-%", "name": self.name or ""},
            as_dict=True,
        )

        next_number = 1
        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
        for row in existing_numbers:
            match = pattern.match(row.invoice_number or "")
            if match:
                next_number = max(next_number, int(match.group(1)) + 1)

        return f"{prefix}-{next_number}"

    def get_invoice_prefix(self):
        reference = (self.reference or "").strip()
        if reference:
            return clean_invoice_prefix(reference)

        if self.customer:
            customer_code = frappe.db.get_value("Customer", self.customer, "esrm_customer_code")
            short_name = frappe.db.get_value("Customer", self.customer, "esrm_short_name")
            customer_name = customer_code or short_name or self.customer
            if customer_name:
                return clean_invoice_prefix(customer_name)

        return "OTHERS"

    def set_route_summary(self):
        self.route_summary = build_route_summary(self.sectors, self.trip_type)

    def sync_invoice_details(self):
        if not self.sales_invoice:
            self.invoice_status = "Not Invoiced"
            self.outstanding_amount = flt(self.invoice_amount) - flt(self.paid_amount)
            return

        invoice = frappe.db.get_value(
            "Sales Invoice",
            self.sales_invoice,
            ["name", "status", "grand_total", "outstanding_amount", "docstatus"],
            as_dict=True,
        )
        if not invoice:
            self.sales_invoice = None
            self.invoice_status = "Not Invoiced"
            self.outstanding_amount = flt(self.invoice_amount) - flt(self.paid_amount)
            return

        invoice_amount = get_booking_invoice_row_amount(self.name, self.sales_invoice) or flt(invoice.grand_total)
        paid_ratio = 0
        if flt(invoice.grand_total) > 0:
            paid_ratio = max(flt(invoice.grand_total) - flt(invoice.outstanding_amount), 0) / flt(invoice.grand_total)

        self.invoice_status = invoice.status or "Draft"
        is_administrator_amendment = (
            frappe.session.user == "Administrator"
            and self.docstatus == 1
            and self.approval_status == "Approved"
            and self.has_value_changed("amendment_reason")
        )
        if not is_administrator_amendment:
            self.invoice_amount = invoice_amount
        else:
            invoice_amount = flt(self.invoice_amount)
        self.outstanding_amount = max(invoice_amount - (invoice_amount * paid_ratio), 0)
        self.paid_amount = max(flt(self.invoice_amount) - flt(self.outstanding_amount), 0)

    def set_status(self):
        if self.docstatus == 2:
            self.status = "Cancelled"
            return

        if self.cancellation_status and self.cancellation_status != "Active":
            self.status = (
                "Refunded" if self.cancellation_status == "Refunded" else "Cancelled"
            )
            return

        if self.sales_invoice:
            if flt(self.outstanding_amount) <= 0 and flt(self.invoice_amount) > 0:
                self.status = "Paid"
            elif flt(self.paid_amount) > 0:
                self.status = "Partially Paid"
            else:
                self.status = "Invoiced"
            return

        flight_date = getdate(self.flight_date) if self.flight_date else None
        today = getdate(nowdate())

        if flight_date and flight_date < today:
            self.status = "Travelled"
        else:
            if self.status in {"Invoiced", "Partially Paid", "Paid", "Cancelled"} or not self.status:
                self.status = "Draft"


@frappe.whitelist()
def make_sales_invoice(source_name):
    booking = frappe.get_doc("Ticket Booking", source_name)

    if booking.sales_invoice:
        return booking.sales_invoice

    return make_and_submit_sales_invoice([booking.name])


@frappe.whitelist()
def create_ticket_credit_note(
    source_name, refund_amount, cancellation_fee=0, cancellation_date=None,
    cancellation_reason=None
):
    """Create a draft credit note for one ticket on a submitted Sales Invoice."""
    if frappe.session.user != "Administrator":
        frappe.throw(
            _("Only Administrator can cancel a ticket and create its credit note."),
            frappe.PermissionError,
        )

    booking = frappe.get_doc("Ticket Booking", source_name)
    if booking.docstatus != 1 or booking.approval_status != "Approved":
        frappe.throw(_("Only an approved, submitted Ticket Booking can be cancelled."))
    if not booking.sales_invoice:
        frappe.throw(_("Create the Sales Invoice before cancelling this ticket."))
    if booking.credit_note:
        frappe.throw(
            _("Credit Note {0} already exists for this booking.").format(
                booking.credit_note
            )
        )

    original_invoice = frappe.get_doc("Sales Invoice", booking.sales_invoice)
    if original_invoice.docstatus == 2 or original_invoice.is_return:
        frappe.throw(_("The linked original Sales Invoice cannot be cancelled or a return."))

    original_amount = get_booking_invoice_row_amount(booking.name, original_invoice.name)
    if original_amount <= 0:
        frappe.throw(_("The original ticket amount could not be determined."))

    refund_amount = flt(refund_amount)
    cancellation_fee = flt(cancellation_fee)
    if refund_amount <= 0:
        frappe.throw(_("Refund Before Cancellation Fee must be greater than zero."))
    if refund_amount > original_amount:
        frappe.throw(
            _("Refund Before Cancellation Fee cannot exceed {0}.").format(
                frappe.format_value(original_amount, {"fieldtype": "Currency"})
            )
        )
    if cancellation_fee < 0 or cancellation_fee >= refund_amount:
        frappe.throw(_("Cancellation Fee must be zero or less than the refund amount."))

    net_credit = refund_amount - cancellation_fee
    revised_amount = original_amount - net_credit

    cancellation_values = {
        "cancellation_date": cancellation_date or nowdate(),
        "cancellation_reason": (cancellation_reason or "").strip(),
        "refund_amount": refund_amount,
        "cancellation_fee": cancellation_fee,
        "net_credit_amount": net_credit,
        "revised_invoice_amount": revised_amount,
        "status": "Cancelled",
    }

    if original_invoice.docstatus == 0:
        revise_draft_invoice_for_cancellation(
            booking,
            original_invoice,
            revised_amount,
            refund_amount,
            cancellation_fee,
            cancellation_values["cancellation_reason"],
        )
        cancellation_values.update(
            {
                "cancellation_status": "Draft Invoice Revised",
                "invoice_status": "Draft",
            }
        )
        frappe.db.set_value(
            "Ticket Booking",
            booking.name,
            cancellation_values,
            update_modified=True,
        )
        booking.add_comment(
            "Info",
            _("Draft Sales Invoice {0} revised after ticket cancellation.").format(
                original_invoice.name
            ),
        )
        return {"name": original_invoice.name, "document_type": "Updated Invoice"}

    from erpnext.controllers.sales_and_purchase_return import make_return_doc

    credit_note = make_return_doc("Sales Invoice", original_invoice.name)
    original_ticket_row = next(
        (
            row
            for row in original_invoice.get("esrm_ticket_bookings") or []
            if row.ticket_booking == booking.name
        ),
        None,
    )
    if not original_ticket_row:
        frappe.throw(_("The ticket row is missing from the original Sales Invoice."))

    original_item = next(
        (row for row in original_invoice.items if row.idx == original_ticket_row.idx),
        None,
    )
    if not original_item:
        frappe.throw(_("The matching invoice item is missing from the original invoice."))

    return_item = next(
        (
            row
            for row in credit_note.items
            if row.sales_invoice_item == original_item.name
        ),
        None,
    )
    if not return_item:
        frappe.throw(_("ERPNext could not create the matching return item."))

    credit_note.items = [return_item]
    return_item.qty = -1
    return_item.rate = net_credit
    return_item.description = _("Refund for cancelled ticket {0}; cancellation fee {1}").format(
        booking.ticket_number or booking.name,
        frappe.format_value(cancellation_fee, {"fieldtype": "Currency"}),
    )
    credit_note.esrm_invoice_number = booking.invoice_number
    credit_note.esrm_ticket_booking = booking.name
    credit_note.set("esrm_ticket_bookings", [])
    credit_note.append(
        "esrm_ticket_bookings",
        build_invoice_ticket_row(
            booking,
            -refund_amount,
            remarks=_("REFUND"),
        ),
    )
    if cancellation_fee:
        fee_row = build_invoice_ticket_row(
            booking, cancellation_fee, remarks=_("CANCELLATION FEE")
        )
        fee_row.update(
            {
                "issue_date": cancellation_date or nowdate(),
                "passenger_name": "",
                "ticket_number": "",
                "route": "",
                "carrier": "",
            }
        )
        credit_note.append("esrm_ticket_bookings", fee_row)
    credit_note.remarks = _(
        "Credit note for cancelled Ticket Booking {0}. Refund before fee: {1}; "
        "cancellation fee: {2}; net credit: {3}. Reason: {4}"
    ).format(
        booking.name,
        refund_amount,
        cancellation_fee,
        net_credit,
        (cancellation_reason or "").strip(),
    )
    credit_note.insert(ignore_permissions=True)

    cancellation_values.update(
        {
            "cancellation_status": "Credit Note Draft",
            "credit_note": credit_note.name,
        }
    )
    frappe.db.set_value(
        "Ticket Booking",
        booking.name,
        cancellation_values,
        update_modified=True,
    )
    booking.add_comment(
        "Info",
        _("Draft Credit Note {0} created for net credit {1}.").format(
            credit_note.name, net_credit
        ),
    )
    return {"name": credit_note.name, "document_type": "Credit Note"}


def revise_draft_invoice_for_cancellation(
    booking, invoice, revised_amount, refund_amount, cancellation_fee, reason
):
    ticket_row = next(
        (
            row
            for row in invoice.get("esrm_ticket_bookings") or []
            if row.ticket_booking == booking.name
        ),
        None,
    )
    if not ticket_row:
        frappe.throw(_("The ticket row is missing from the draft Sales Invoice."))
    item = next((row for row in invoice.items if row.idx == ticket_row.idx), None)
    if not item:
        frappe.throw(_("The matching item is missing from the draft Sales Invoice."))

    item.rate = revised_amount
    item.description = _(
        "Cancelled ticket {0}; refund {1}; cancellation fee {2}. Reason: {3}"
    ).format(
        booking.ticket_number or booking.name,
        refund_amount,
        cancellation_fee,
        reason,
    )
    ticket_row.fare = revised_amount
    ticket_row.remarks = _("CANCELLED / REFUND")

    # Saving an older draft makes ERPNext validate its historical dates again.
    # Preserve its posting date and ensure every due date is valid for that date.
    if invoice.meta.has_field("set_posting_time"):
        invoice.set_posting_time = 1
    posting_date = getdate(invoice.posting_date or nowdate())
    if not invoice.due_date or getdate(invoice.due_date) < posting_date:
        invoice.due_date = posting_date
    for payment in invoice.get("payment_schedule") or []:
        if not payment.due_date or getdate(payment.due_date) < posting_date:
            payment.due_date = posting_date

    invoice.remarks = "\n\n".join(
        filter(
            None,
            [
                invoice.remarks,
                _(
                    "Ticket Booking {0} cancelled. Refund: {1}; fee: {2}; revised amount: {3}."
                ).format(
                    booking.name, refund_amount, cancellation_fee, revised_amount
                ),
            ],
        )
    )
    invoice.flags.ignore_permissions = True
    invoice.save()


@frappe.whitelist()
def make_group_sales_invoice(bookings):
    if isinstance(bookings, str):
        import json

        bookings = json.loads(bookings)

    return consolidate_invoiced_bookings(bookings)


def consolidate_invoiced_bookings(booking_names):
    """Replace individual unpaid booking invoices with one submitted invoice."""
    if frappe.session.user != "Administrator":
        frappe.throw(
            _("Only Administrator can consolidate submitted Sales Invoices."),
            frappe.PermissionError,
        )

    booking_names = list(dict.fromkeys(booking_names or []))
    if len(booking_names) < 2:
        frappe.throw(_("Select at least two Ticket Bookings to consolidate."))
    if len(booking_names) > 100:
        frappe.throw(_("Consolidate no more than 100 Ticket Bookings at a time."))

    bookings = [frappe.get_doc("Ticket Booking", name) for name in booking_names]
    invoices = validate_bookings_for_consolidation(bookings)
    consolidated_invoice_number = bookings[0].get_next_invoice_number()
    cancelled_invoice_names = [invoice.name for invoice in invoices]

    # Frappe rolls the request back as one transaction if any cancellation,
    # invoice insert, or submission fails.
    from esrm_travel.workflow import cancel_sales_invoice

    for invoice in invoices:
        cancel_sales_invoice(invoice.name)

    invoice_name = make_and_submit_sales_invoice(
        booking_names,
        invoice_number=consolidated_invoice_number,
    )
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    invoice.add_comment(
        "Info",
        _("Consolidated from cancelled Sales Invoices: {0}").format(
            ", ".join(cancelled_invoice_names)
        ),
    )
    for booking in bookings:
        frappe.get_doc("Ticket Booking", booking.name).add_comment(
            "Info",
            _("Individual invoice replaced by consolidated Sales Invoice {0}.").format(
                invoice_name
            ),
        )

    return invoice_name


def validate_bookings_for_consolidation(bookings):
    customer = None
    company = None
    currency = None
    invoices = []
    invoice_names = set()

    for booking in bookings:
        if booking.docstatus != 1 or booking.approval_status != "Approved":
            frappe.throw(
                _("Ticket Booking {0} must be approved and submitted.").format(
                    booking.name
                )
            )
        if not booking.sales_invoice:
            frappe.throw(
                _("Ticket Booking {0} does not have an individual Sales Invoice.").format(
                    booking.name
                )
            )

        invoice = frappe.get_doc("Sales Invoice", booking.sales_invoice)
        if invoice.name in invoice_names:
            frappe.throw(
                _("The selected bookings are already linked to the same Sales Invoice {0}.").format(
                    invoice.name
                )
            )
        invoice_names.add(invoice.name)

        if invoice.docstatus != 1 or invoice.is_return:
            frappe.throw(
                _("Sales Invoice {0} must be a submitted standard invoice.").format(
                    invoice.name
                )
            )
        linked_bookings = frappe.get_all(
            "ESRM Invoice Ticket",
            filters={"parent": invoice.name, "parenttype": "Sales Invoice"},
            pluck="ticket_booking",
        )
        if linked_bookings != [booking.name]:
            frappe.throw(
                _("Sales Invoice {0} is not an individual invoice for {1}.").format(
                    invoice.name, booking.name
                )
            )
        if flt(invoice.grand_total) <= 0 or abs(
            flt(invoice.outstanding_amount) - flt(invoice.grand_total)
        ) > 0.005:
            frappe.throw(
                _("Sales Invoice {0} has a payment or allocation and cannot be consolidated.").format(
                    invoice.name
                )
            )
        if frappe.db.exists(
            "Payment Entry Reference",
            {
                "reference_doctype": "Sales Invoice",
                "reference_name": invoice.name,
                "docstatus": 1,
            },
        ):
            frappe.throw(
                _("Sales Invoice {0} is referenced by a submitted Payment Entry.").format(
                    invoice.name
                )
            )
        if frappe.db.exists(
            "Sales Invoice",
            {"return_against": invoice.name, "docstatus": 1},
        ):
            frappe.throw(
                _("Sales Invoice {0} has a submitted credit/debit adjustment.").format(
                    invoice.name
                )
            )

        customer = customer or invoice.customer
        company = company or invoice.company
        currency = currency or invoice.currency
        if invoice.customer != customer:
            frappe.throw(_("All selected bookings must have the same customer."))
        if invoice.company != company or invoice.currency != currency:
            frappe.throw(
                _("All selected invoices must have the same company and currency.")
            )
        if booking.customer != customer:
            frappe.throw(
                _("Ticket Booking {0} does not match its invoice customer.").format(
                    booking.name
                )
            )

        invoices.append(invoice)

    return invoices


def make_and_submit_sales_invoice(booking_names, amended_from=None, invoice_number=None):
    invoice_name = make_sales_invoice_from_bookings(
        booking_names,
        amended_from=amended_from,
        invoice_number=invoice_number,
    )
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    invoice.flags.ignore_permissions = True
    invoice.submit()
    return invoice.name


def make_sales_invoice_from_bookings(
    booking_names, amended_from=None, invoice_number=None
):
    if not booking_names:
        frappe.throw(_("Select at least one Ticket Booking."))

    bookings = [frappe.get_doc("Ticket Booking", name) for name in booking_names]
    validate_bookings_for_invoice(bookings)

    settings = frappe.get_single("ESRM Travel Settings")
    validate_invoice_settings(settings)
    company_currency = frappe.db.get_value(
        "Company", settings.default_company, "default_currency"
    ) or "BDT"
    selling_price_list = (
        frappe.db.get_single_value("Selling Settings", "selling_price_list")
        or "Standard Selling"
    )

    invoice_items = []
    invoice_tickets = []
    for booking in bookings:
        rate = flt(booking.invoice_amount) or flt(booking.gross_amount)
        if rate <= 0:
            frappe.throw(_("Invoice Amount or Gross Amount must be greater than zero for Ticket Booking {0}.").format(booking.name))

        item_row = {
            "item_code": settings.default_service_item,
            "qty": 1,
            "rate": rate,
            "description": build_invoice_description(booking),
        }

        if settings.default_cost_center:
            item_row["cost_center"] = settings.default_cost_center
        item_row["income_account"] = get_booking_income_account(booking, settings)

        invoice_items.append(item_row)
        invoice_tickets.append(build_invoice_ticket_row(booking, rate))

    invoice_values = {
            "doctype": "Sales Invoice",
            "customer": bookings[0].customer,
            "company": settings.default_company,
            "currency": company_currency,
            "conversion_rate": 1,
            "selling_price_list": selling_price_list,
            "price_list_currency": company_currency,
            "plc_conversion_rate": 1,
            "posting_date": nowdate(),
            "due_date": get_invoice_due_date(bookings),
            "esrm_invoice_number": invoice_number or bookings[0].invoice_number,
            "items": invoice_items,
            "esrm_ticket_booking": bookings[0].name,
            "esrm_ticket_bookings": invoice_tickets,
            "remarks": "\n\n".join(build_invoice_description(booking) for booking in bookings),
        }
    if amended_from:
        invoice_values["amended_from"] = amended_from

    sales_invoice = frappe.get_doc(invoice_values)
    sales_invoice.insert(ignore_permissions=True)

    for booking in bookings:
        values = {
            "sales_invoice": sales_invoice.name,
            "invoice_status": sales_invoice.status or "Draft",
            "status": "Invoiced",
        }
        if invoice_number:
            values["invoice_number"] = invoice_number
        frappe.db.set_value("Ticket Booking", booking.name, values, update_modified=True)

    return sales_invoice.name


def validate_bookings_for_invoice(bookings):
    customer = None
    already_invoiced = []

    for booking in bookings:
        if booking.sales_invoice:
            already_invoiced.append(f"{booking.name} ({booking.sales_invoice})")
        if booking.approval_status != "Approved":
            frappe.throw(_("Only approved ticket bookings can be invoiced. {0} is {1}.").format(booking.name, booking.approval_status))
        if not booking.customer:
            frappe.throw(_("Customer is required before creating a Sales Invoice for Ticket Booking {0}.").format(booking.name))

        customer = customer or booking.customer
        if booking.customer != customer:
            frappe.throw(_("All selected ticket bookings must have the same customer."))

    if already_invoiced:
        frappe.throw(_("These ticket bookings are already invoiced: {0}").format(", ".join(already_invoiced)))


def validate_invoice_settings(settings):
    if not settings.default_company:
        frappe.throw(_("Set Default Company in ESRM Settings first."))
    if not settings.default_service_item:
        frappe.throw(_("Set Default Service Item in ESRM Settings first."))


def get_booking_income_account(booking, settings):
    if booking.travel_type == "Domestic":
        income_account = settings.domestic_income_account
    elif booking.travel_type == "International":
        income_account = settings.international_income_account
    else:
        frappe.throw(
            _("Select Domestic or International in Travel Type for Ticket Booking {0}.").format(
                booking.name
            )
        )

    if not income_account:
        frappe.throw(
            _("Set the {0} Ticket Income Account in ESRM Settings first.").format(
                booking.travel_type
            )
        )

    return income_account


def get_invoice_due_date(bookings, invoice_posting_date=None):
    dates = [booking.flight_date or booking.issue_date for booking in bookings if booking.flight_date or booking.issue_date]
    posting_date = max(
        getdate(invoice_posting_date or nowdate()),
        getdate(nowdate()),
    )
    booking_due_date = min(getdate(date) for date in dates) if dates else posting_date
    return max(booking_due_date, posting_date)


def build_invoice_ticket_row(booking, rate, remarks=None):
    return {
        "ticket_booking": booking.name,
        "purpose": booking.purpose,
        "reference": booking.reference,
        "issue_date": booking.issue_date,
        "passenger_name": booking.passenger_name,
        "ticket_number": booking.ticket_number,
        "route": booking.route_summary,
        "carrier": get_ticket_carrier(booking),
        "fare": rate,
        "remarks": remarks if remarks is not None else booking.remarks,
    }


def get_ticket_carrier(booking):
    if booking.sectors:
        carriers = []
        for sector in booking.sectors:
            if sector.carrier and sector.carrier not in carriers:
                carriers.append(sector.carrier)
        if carriers:
            return " / ".join(carriers)

    return booking.airline


def get_booking_invoice_row_amount(booking_name, sales_invoice):
    return flt(
        frappe.db.get_value(
            "ESRM Invoice Ticket",
            {
                "parenttype": "Sales Invoice",
                "parent": sales_invoice,
                "ticket_booking": booking_name,
            },
            "fare",
        )
    )


def build_invoice_description(booking):
    parts = [
        f"Invoice No: {booking.invoice_number}" if booking.invoice_number else "",
        f"Passenger: {booking.passenger_name}" if booking.passenger_name else "",
        f"PNR: {booking.pnr}" if booking.pnr else "",
        f"Ticket No: {booking.ticket_number}" if booking.ticket_number else "",
        f"Route: {booking.route_summary}" if booking.route_summary else "",
        f"Airline: {booking.airline}" if booking.airline else "",
        f"Flight Date: {booking.flight_date}" if booking.flight_date else "",
        f"Return Date: {booking.return_date}" if booking.return_date else "",
    ]
    return "\n".join(part for part in parts if part)


def clean_invoice_prefix(value):
    prefix = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().upper()).strip("-")
    return prefix or "OTHERS"


def build_route_summary(sectors, trip_type="One Way"):
    airports = []
    for sector in sectors or []:
        origin = (sector.origin or "").strip().upper()
        destination = (sector.destination or "").strip().upper()
        if not origin or not destination:
            continue

        if not airports:
            airports.extend([origin, destination])
        elif airports[-1] == origin:
            airports.append(destination)
        else:
            airports.extend([origin, destination])

    if trip_type == "Return" and airports and airports[-1] != airports[0]:
        airports.append(airports[0])

    return "-".join(airports)
