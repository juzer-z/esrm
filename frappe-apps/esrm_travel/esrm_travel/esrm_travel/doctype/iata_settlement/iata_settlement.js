frappe.ui.form.on("IATA Settlement", {
    period_from: load_when_ready,
    period_to: load_when_ready,
    refresh(frm) {
        if (frm.doc.docstatus === 0 && frm.doc.period_from && frm.doc.period_to) {
            frm.add_custom_button(__("Reload Verified Entries"), () => load_entries(frm));
        }
        for (const fieldname of ["international_expense_account", "domestic_expense_account"]) {
            frm.set_query(fieldname, () => ({filters: {company: frm.doc.company, root_type: "Expense", is_group: 0, disabled: 0}}));
        }
        frm.set_query("source_account", "deposits", () => ({filters: {company: frm.doc.company, root_type: "Asset", is_group: 0, disabled: 0}}));
    },
});

frappe.ui.form.on("IATA Settlement Deposit", {
    deposits_add: recalculate_deposits,
    deposits_remove: recalculate_deposits,
    amount: recalculate_deposits,
});

function load_when_ready(frm) {
    if (frm.doc.docstatus === 0 && frm.doc.period_from && frm.doc.period_to) load_entries(frm);
}

function load_entries(frm) {
    Promise.all([
        frappe.call({method: "esrm_travel.esrm_travel.doctype.iata_settlement.iata_settlement.get_eligible_bookings", args: {period_from: frm.doc.period_from, period_to: frm.doc.period_to, current_settlement: frm.doc.name}}),
        frappe.call({method: "esrm_travel.esrm_travel.doctype.iata_settlement.iata_settlement.get_eligible_memos", args: {period_from: frm.doc.period_from, period_to: frm.doc.period_to, current_settlement: frm.doc.name}}),
    ]).then(([bookingResponse, memoResponse]) => {
        frm.clear_table("bookings");
        frm.clear_table("registered_memos");
        let domestic = 0;
        let international = 0;
        for (const booking of bookingResponse.message || []) {
            const row = frm.add_child("bookings", booking);
            row.expense_account = booking.travel_type === "Domestic" ? frm.doc.domestic_expense_account : frm.doc.international_expense_account;
            if (booking.travel_type === "Domestic") domestic += flt(booking.iata_amount);
            else international += flt(booking.iata_amount);
        }
        for (const memo of memoResponse.message || []) {
            frm.add_child("registered_memos", memo);
            if (memo.travel_type === "Domestic") domestic += flt(memo.amount);
            else international += flt(memo.amount);
        }
        frm.set_value("domestic_amount", domestic);
        frm.set_value("international_amount", international);
        frm.set_value("expected_total", domestic + international);
        recalculate_deposits(frm);
        frm.refresh_fields();
        frappe.show_alert({message: __("Loaded {0} booking entries and {1} ACM/ADM memos.", [(bookingResponse.message || []).length, (memoResponse.message || []).length]), indicator: "green"});
    });
}

function recalculate_deposits(frm) {
    const deposited = (frm.doc.deposits || []).reduce((total, row) => total + flt(row.amount), 0);
    frm.set_value("deposit_amount", deposited);
    frm.set_value("difference_amount", deposited - flt(frm.doc.expected_total));
}
