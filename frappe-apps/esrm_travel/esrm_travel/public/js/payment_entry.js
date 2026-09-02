frappe.ui.form.on("Payment Entry", {
    refresh(frm) {
        if (
            frm.doc.docstatus !== 0 ||
            frm.doc.payment_type !== "Receive" ||
            frm.doc.party_type !== "Customer" ||
            !frm.doc.party
        ) {
            return;
        }

        frm.add_custom_button(__("Load Invoices by Reference"), () => {
            const dialog = new frappe.ui.Dialog({
                title: __("Load Outstanding Invoices"),
                fields: [
                    {
                        fieldname: "references",
                        fieldtype: "Small Text",
                        label: __("Invoice References"),
                        description: __("Paste ERP invoice IDs or customer invoice numbers, separated by lines, commas, or semicolons."),
                        reqd: 1,
                    },
                ],
                primary_action_label: __("Load Invoices"),
                primary_action(values) {
                    frappe.call({
                        method: "esrm_travel.payment_reconciliation.get_outstanding_invoices_by_reference",
                        args: {
                            party: frm.doc.party,
                            company: frm.doc.company,
                            references: values.references,
                        },
                        freeze: true,
                        freeze_message: __("Finding outstanding invoices..."),
                        callback(response) {
                            const result = response.message || {};
                            const invoices = result.invoices || [];
                            if (!invoices.length) {
                                show_resolution_message(result);
                                return;
                            }

                            const load = () => {
                                frm.clear_table("references");
                                invoices.forEach((invoice) => {
                                    const row = frm.add_child("references");
                                    row.reference_doctype = "Sales Invoice";
                                    row.reference_name = invoice.name;
                                    row.due_date = invoice.due_date;
                                    row.total_amount = invoice.rounded_total || invoice.grand_total;
                                    row.outstanding_amount = invoice.outstanding_amount;
                                    row.allocated_amount = invoice.outstanding_amount;
                                });
                                frm.refresh_field("references");
                                frm.trigger("set_total_allocated_amount");
                                dialog.hide();
                                show_resolution_message(result);
                                frappe.show_alert({
                                    message: __("Loaded {0} invoices; allocated total {1}.", [
                                        invoices.length,
                                        format_currency(result.total_outstanding, frm.doc.paid_from_account_currency || frm.doc.paid_to_account_currency),
                                    ]),
                                    indicator: "green",
                                });
                            };

                            if ((frm.doc.references || []).length) {
                                frappe.confirm(
                                    __("Replace the invoice rows currently in this Payment Entry?"),
                                    load
                                );
                            } else {
                                load();
                            }
                        },
                    });
                },
            });
            dialog.show();
        }, __("Get Outstanding"));
    },
});

function show_resolution_message(result) {
    const lines = [];
    if ((result.missing || []).length) {
        lines.push(__("Not found or no longer outstanding: {0}", [result.missing.join(", ")]));
    }
    (result.ambiguous || []).forEach((item) => {
        lines.push(__("Reference {0} matches multiple invoices: {1}", [item.reference, item.invoices.join(", ")]));
    });
    if (lines.length) {
        frappe.msgprint({
            title: __("Some references need attention"),
            message: lines.map((line) => `<div>${frappe.utils.escape_html(line)}</div>`).join(""),
            indicator: "orange",
        });
    }
}
