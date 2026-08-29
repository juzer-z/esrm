frappe.ui.form.on("IATA Settlement", {
    period_from(frm) {
        load_bookings_when_ready(frm);
    },
    period_to(frm) {
        load_bookings_when_ready(frm);
    },
    deposit_amount(frm) {
        frm.set_value(
            "difference_amount",
            flt(frm.doc.deposit_amount) - flt(frm.doc.expected_total),
        );
    },
    refresh(frm) {
        if (frm.doc.docstatus === 0 && frm.doc.period_from && frm.doc.period_to) {
            frm.add_custom_button(__("Load Eligible Bookings"), () => load_bookings(frm));
        }
        frm.set_query("source_account", () => ({
            filters: { company: frm.doc.company, root_type: "Asset", is_group: 0, disabled: 0 },
        }));
        for (const fieldname of ["international_expense_account", "domestic_expense_account"]) {
            frm.set_query(fieldname, () => ({
                filters: { company: frm.doc.company, root_type: "Expense", is_group: 0, disabled: 0 },
            }));
        }
    },
});

function load_bookings_when_ready(frm) {
    if (frm.doc.docstatus === 0 && frm.doc.period_from && frm.doc.period_to) {
        load_bookings(frm);
    }
}

function load_bookings(frm) {
    frappe.call({
        method: "esrm_travel.esrm_travel.doctype.iata_settlement.iata_settlement.get_eligible_bookings",
        args: {
            period_from: frm.doc.period_from,
            period_to: frm.doc.period_to,
            current_settlement: frm.doc.name,
        },
        freeze: true,
        freeze_message: __("Loading unsettled IATA bookings..."),
        callback(r) {
            frm.clear_table("bookings");
            let domestic = 0;
            let international = 0;
            for (const booking of r.message || []) {
                const row = frm.add_child("bookings", booking);
                row.expense_account = booking.travel_type === "Domestic"
                    ? frm.doc.domestic_expense_account
                    : frm.doc.international_expense_account;
                if (booking.travel_type === "Domestic") domestic += flt(booking.iata_amount);
                else international += flt(booking.iata_amount);
            }
            frm.set_value("domestic_amount", domestic);
            frm.set_value("international_amount", international);
            frm.set_value("expected_total", domestic + international);
            frm.set_value("deposit_amount", domestic + international);
            frm.set_value("difference_amount", 0);
            frm.refresh_fields();
        },
    });
}
