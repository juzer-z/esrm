frappe.ui.form.on("Employee Advance", {
    refresh(frm) {
        const roles = frappe.user_roles || [];
        const is_accounts = roles.includes("ESRM Accounts") || roles.includes("System Manager");

        if (!is_accounts) {
            frm.set_df_property("employee", "read_only", 1);
            frm.set_df_property("advance_account", "hidden", 1);
            frm.set_df_property("mode_of_payment", "hidden", 1);
            frm.set_df_property("repay_unclaimed_amount_from_salary", "hidden", 1);
            if (frm.is_new() && !frm.__esrm_defaults_loaded) {
                frm.__esrm_defaults_loaded = true;
                frappe.call({
                    method: "esrm_travel.cash_advance.get_employee_advance_request_defaults",
                    callback(r) {
                        if (!r.message) return;
                        Object.assign(frm.doc, r.message);
                        frm.refresh_fields([
                            "employee", "employee_name", "company", "department",
                            "currency", "advance_account",
                        ]);
                        frm.dirty();
                    },
                });
            }
        }


        if (
            is_accounts &&
            frm.doc.docstatus === 1 &&
            frm.doc.workflow_state === "Approved" &&
            flt(frm.doc.paid_amount) < flt(frm.doc.advance_amount)
        ) {
            frm.add_custom_button(__("Disburse Advance"), () => {
                frappe.call({
                    method: "esrm_travel.cash_advance.get_cash_disbursement_defaults",
                    args: { employee_advance: frm.doc.name },
                    callback(r) {
                        if (!r.message) return;
                        const defaults = r.message;
                        const dialog = new frappe.ui.Dialog({
                            title: __("Disburse Advance"),
                            fields: [
                                {
                                    fieldname: "disbursement_account",
                                    label: __("Pay From"),
                                    fieldtype: "Link",
                                    options: "Account",
                                    reqd: 1,
                                    default: defaults.account,
                                    get_query: () => ({
                                        filters: {
                                            company: frm.doc.company,
                                            is_group: 0,
                                            disabled: 0,
                                            account_type: ["in", ["Cash", "Bank"]],
                                        },
                                    }),
                                },
                                {
                                    fieldname: "posting_date",
                                    label: __("Disbursement Date"),
                                    fieldtype: "Date",
                                    reqd: 1,
                                    default: defaults.posting_date,
                                },
                                {
                                    fieldname: "amount",
                                    label: __("Amount"),
                                    fieldtype: "Currency",
                                    options: frm.doc.currency || "BDT",
                                    reqd: 1,
                                    default: defaults.amount,
                                },
                                {
                                    fieldname: "reference_no",
                                    label: __("Transaction Reference (for bank payment)"),
                                    fieldtype: "Data",
                                },
                            ],
                            primary_action_label: __("Disburse and Post"),
                            primary_action(values) {
                                dialog.disable_primary_action();
                                frappe.call({
                                    method: "esrm_travel.cash_advance.disburse_cash_advance",
                                    args: {
                                        employee_advance: frm.doc.name,
                                        ...values,
                                    },
                                    freeze: true,
                                    freeze_message: __("Posting cash disbursement..."),
                                    callback(result) {
                                        if (!result.message) return;
                                        dialog.hide();
                                        frappe.show_alert({
                                            message: __("Journal Entry {0} submitted", [result.message.journal_entry]),
                                            indicator: "green",
                                        });
                                        frm.reload_doc();
                                    },
                                    always() {
                                        dialog.enable_primary_action();
                                    },
                                });
                            },
                        });
                        dialog.show();
                    },
                });
            });
            frm.change_custom_button_type(__("Disburse Advance"), null, "primary");
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

    after_workflow_action(frm) {
        esrm_offer_manual_whatsapp(frm, "workflow");
    },
});
