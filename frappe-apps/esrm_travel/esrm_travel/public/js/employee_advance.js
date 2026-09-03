frappe.ui.form.on("Employee Advance", {
    refresh(frm) {
        const roles = frappe.user_roles || [];
        const is_accounts = roles.includes("ESRM Accounts") || roles.includes("System Manager");

        if (!is_accounts) {
            frm.set_df_property("employee", "read_only", 1);
            frm.set_df_property("advance_account", "hidden", 1);
            frm.set_df_property("mode_of_payment", "hidden", 1);
            if (frm.is_new() && !frm.doc.employee) {
                const employee = frappe.defaults.get_user_default("Employee");
                if (employee) frm.set_value("employee", employee);
            }
        }

        if (
            frm.doc.docstatus === 1 &&
            flt(frm.doc.paid_amount) > flt(frm.doc.claimed_amount) + flt(frm.doc.return_amount) &&
            frappe.model.can_create("Expense Claim")
        ) {
            frm.add_custom_button(__("Submit Expenses"), () => {
                frappe.call({
                    method: "esrm_travel.cash_advance.make_cash_expense_claim",
                    args: { employee_advance: frm.doc.name },
                    freeze: true,
                    callback(r) {
                        if (!r.message) return;
                        const docs = frappe.model.sync(r.message);
                        frappe.set_route("Form", docs[0].doctype, docs[0].name);
                    },
                });
            });
        }

        if (
            frm.doc.docstatus === 1 &&
            frm.doc.custom_settlement_due_date &&
            frappe.datetime.get_diff(frappe.datetime.nowdate(), frm.doc.custom_settlement_due_date) > 0 &&
            flt(frm.doc.paid_amount) > flt(frm.doc.claimed_amount) + flt(frm.doc.return_amount)
        ) {
            frm.dashboard.set_headline_alert(
                __("Settlement overdue since {0}.", [frappe.datetime.str_to_user(frm.doc.custom_settlement_due_date)]),
                "red",
            );
        }
    },
});
