import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, nowdate


COMPANY = "Ezzy Services & Resource Management"
PETTY_CASH_ACCOUNT = "Petty Cash - ESRM"
INTERNATIONAL_EXPENSE_ACCOUNT = "Air Ticket Purchase- International - ESRM"
DOMESTIC_EXPENSE_ACCOUNT = "Air Ticket Purchase -Domestic - ESRM"


class IATASettlement(Document):
    def autoname(self):
        self.naming_series = self.naming_series or "IATA-SET-.YYYY.-"
        self.name = make_autoname(self.naming_series)

    def before_validate(self):
        self.company = self.company or COMPANY
        self.source_account = self.source_account or PETTY_CASH_ACCOUNT
        self.international_expense_account = (
            self.international_expense_account or INTERNATIONAL_EXPENSE_ACCOUNT
        )
        self.domestic_expense_account = (
            self.domestic_expense_account or DOMESTIC_EXPENSE_ACCOUNT
        )
        self.deposit_date = self.deposit_date or nowdate()
        self.currency = (
            frappe.db.get_value("Company", self.company, "default_currency") or "BDT"
        )
        if self.docstatus == 0 and self.period_from and self.period_to:
            self.populate_eligible_bookings()

    def validate(self):
        self.validate_period()
        self.validate_accounts()
        self.calculate_totals()
        self.status = "Draft" if self.docstatus == 0 else self.status

    def before_submit(self):
        self.populate_eligible_bookings()
        self.calculate_totals()
        if not self.bookings:
            frappe.throw(_("No unsettled approved IATA bookings exist in this period."))
        if not self.deposit_slip:
            frappe.throw(_("Attach the cash deposit slip before submitting."))
        if flt(self.deposit_amount) <= 0:
            frappe.throw(_("Cash Deposited must be greater than zero."))
        if abs(flt(self.difference_amount)) > 0.01:
            frappe.throw(
                _("Cash Deposited must equal the Expected IATA Total. Difference: {0}").format(
                    frappe.utils.fmt_money(self.difference_amount, currency=self.currency)
                )
            )
        self.validate_not_already_settled()

    def on_submit(self):
        journal_entry = self.create_journal_entry()
        self.db_set({"journal_entry": journal_entry, "status": "Submitted"})
        self.mark_bookings_settled()

    def before_cancel(self):
        if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
            journal = frappe.get_doc("Journal Entry", self.journal_entry)
            if journal.docstatus == 1:
                journal.flags.ignore_permissions = True
                journal.cancel()

    def on_cancel(self):
        self.db_set("status", "Cancelled")
        for row in self.bookings:
            current = frappe.db.get_value(
                "Ticket Booking", row.ticket_booking, "iata_settlement"
            )
            if current == self.name:
                frappe.db.set_value(
                    "Ticket Booking",
                    row.ticket_booking,
                    {"iata_settlement": None, "iata_settlement_status": "Unsettled"},
                    update_modified=False,
                )

    def validate_period(self):
        if self.period_from and self.period_to and getdate(self.period_from) > getdate(self.period_to):
            frappe.throw(_("Issue Date From cannot be after Issue Date To."))

    def validate_accounts(self):
        checks = (
            (self.source_account, "Asset", _("Paid From")),
            (self.international_expense_account, "Expense", _("International Ticket Expense")),
            (self.domestic_expense_account, "Expense", _("Domestic Ticket Expense")),
        )
        for account, root_type, label in checks:
            values = frappe.db.get_value(
                "Account", account, ["company", "root_type", "is_group", "disabled"], as_dict=True
            )
            if not values or values.company != self.company or values.root_type != root_type or values.is_group or values.disabled:
                frappe.throw(_("{0} must be an active non-group {1} account for {2}.").format(label, root_type, self.company))

    def populate_eligible_bookings(self):
        rows = get_eligible_bookings(self.period_from, self.period_to, self.name)
        self.set("bookings", [])
        for row in rows:
            row["expense_account"] = (
                self.domestic_expense_account
                if row.travel_type == "Domestic"
                else self.international_expense_account
            )
            self.append("bookings", row)
        self.calculate_totals()
        if not flt(self.deposit_amount):
            self.deposit_amount = self.expected_total

    def calculate_totals(self):
        self.domestic_amount = sum(
            flt(row.iata_amount) for row in self.bookings if row.travel_type == "Domestic"
        )
        self.international_amount = sum(
            flt(row.iata_amount) for row in self.bookings if row.travel_type != "Domestic"
        )
        self.expected_total = flt(self.domestic_amount) + flt(self.international_amount)
        self.difference_amount = flt(self.deposit_amount) - flt(self.expected_total)

    def validate_not_already_settled(self):
        names = [row.ticket_booking for row in self.bookings]
        if not names:
            return
        conflicts = frappe.db.sql(
            """
            select name, iata_settlement
            from `tabTicket Booking`
            where name in %(names)s
              and ifnull(iata_settlement, '') not in ('', %(current_settlement)s)
            """,
            {"names": names, "current_settlement": self.name},
            as_dict=True,
        )
        if conflicts:
            frappe.throw(
                _("These bookings are already settled: {0}").format(
                    ", ".join(f"{row.name} ({row.iata_settlement})" for row in conflicts)
                )
            )

    def create_journal_entry(self):
        settings = frappe.get_single("ESRM Travel Settings")
        accounts = []
        for account, amount in (
            (self.international_expense_account, self.international_amount),
            (self.domestic_expense_account, self.domestic_amount),
        ):
            if flt(amount):
                row = {"account": account, "debit_in_account_currency": flt(amount)}
                if settings.default_cost_center:
                    row["cost_center"] = settings.default_cost_center
                accounts.append(row)
        accounts.append(
            {"account": self.source_account, "credit_in_account_currency": flt(self.deposit_amount)}
        )
        journal = frappe.get_doc(
            {
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "company": self.company,
                "posting_date": self.deposit_date,
                "user_remark": _("IATA cash settlement {0}, period {1} to {2}, reference {3}").format(
                    self.name, self.period_from, self.period_to, self.reference_no
                ),
                "accounts": accounts,
            }
        )
        journal.insert(ignore_permissions=True)
        journal.flags.ignore_permissions = True
        journal.submit()
        return journal.name

    def mark_bookings_settled(self):
        for row in self.bookings:
            frappe.db.set_value(
                "Ticket Booking",
                row.ticket_booking,
                {"iata_settlement": self.name, "iata_settlement_status": "Settled"},
                update_modified=False,
            )


@frappe.whitelist()
def get_eligible_bookings(period_from, period_to, current_settlement=None):
    if not period_from or not period_to:
        return []
    if getdate(period_from) > getdate(period_to):
        frappe.throw(_("Issue Date From cannot be after Issue Date To."))
    return frappe.db.sql(
        """
        select
            tb.name as ticket_booking, tb.issue_date, tb.travel_type,
            tb.passenger_name, tb.ticket_number, tb.route_summary, tb.iata_amount
        from `tabTicket Booking` tb
        where tb.docstatus = 1
          and tb.approval_status = 'Approved'
          and tb.payment_mode = 'IATA'
          and ifnull(tb.iata_amount, 0) > 0
          and tb.issue_date between %(period_from)s and %(period_to)s
          and (
              ifnull(tb.iata_settlement, '') = ''
              or tb.iata_settlement = %(current_settlement)s
          )
        order by tb.issue_date, tb.name
        """,
        {
            "period_from": period_from,
            "period_to": period_to,
            "current_settlement": current_settlement or "",
        },
        as_dict=True,
    )
