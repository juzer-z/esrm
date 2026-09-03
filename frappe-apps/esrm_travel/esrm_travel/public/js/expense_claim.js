frappe.ui.form.on("Expense Claim", {
    refresh(frm) {
        const roles = frappe.user_roles || [];
        const is_accounts = roles.includes("ESRM Accounts") || roles.includes("System Manager");
        if (!is_accounts) {
            frm.set_df_property("employee", "read_only", 1);
            frm.set_df_property("payable_account", "hidden", 1);
            frm.set_df_property("is_paid", "hidden", 1);
            frm.set_df_property("mode_of_payment", "hidden", 1);
        }

        if (frm.doc.custom_cash_advance && frm.doc.docstatus === 0) {
            const variance = flt(frm.doc.custom_settlement_variance);
            if (variance > 0) {
                frm.dashboard.set_headline_alert(
                    __("Expenses exceed the advance by {0}. Accounts review is required.", [format_currency(variance)]),
                    "orange",
                );
            } else if (variance < 0) {
                frm.dashboard.set_headline_alert(
                    __("Cash return due: {0}. Submit expenses now; Accounts will record the returned cash.", [format_currency(Math.abs(variance))]),
                    "blue",
                );
            }
        }
    },
});

frappe.ui.form.on("Expense Claim Detail", {
    expense_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.expense_type) {
            frappe.show_alert({ message: __("Attach supporting evidence for this expense row."), indicator: "blue" });
        }
    },
});
