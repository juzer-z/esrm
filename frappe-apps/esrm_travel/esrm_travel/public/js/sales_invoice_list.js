const sales_invoice_list_settings =
    frappe.listview_settings["Sales Invoice"] || {};
const sales_invoice_previous_onload = sales_invoice_list_settings.onload;

sales_invoice_list_settings.onload = function (listview) {
    if (sales_invoice_previous_onload) {
        sales_invoice_previous_onload(listview);
    }

    if (frappe.session.user !== "Administrator") {
        return;
    }

    listview.page.add_actions_menu_item(
        __("Submit Selected Invoices"),
        () => submit_selected_invoices(listview)
    );
};

frappe.listview_settings["Sales Invoice"] = sales_invoice_list_settings;

function submit_selected_invoices(listview) {
    const selected = listview.get_checked_items();
    const drafts = selected.filter((row) => Number(row.docstatus) === 0);

    if (!selected.length) {
        frappe.msgprint(__("Select at least one draft Sales Invoice."));
        return;
    }
    if (drafts.length !== selected.length) {
        frappe.msgprint(__("Select draft Sales Invoices only."));
        return;
    }

    frappe.confirm(
        __("Submit {0} selected Sales Invoice(s)? This creates accounting entries and cannot be undone without cancellation.", [drafts.length]),
        () => {
            frappe.call({
                method: "esrm_travel.workflow.bulk_submit_sales_invoices",
                args: {
                    invoice_names: drafts.map((row) => row.name),
                },
                freeze: true,
                freeze_message: __("Submitting Sales Invoices..."),
                callback: (response) => {
                    const result = response.message || {};
                    const submitted = result.submitted || [];
                    const failed = result.failed || [];

                    if (submitted.length) {
                        frappe.show_alert({
                            message: __("{0} Sales Invoice(s) submitted.", [submitted.length]),
                            indicator: "green",
                        });
                    }

                    if (failed.length) {
                        const details = failed
                            .map((row) => `<li><b>${frappe.utils.escape_html(row.name)}</b>: ${frappe.utils.escape_html(row.error)}</li>`)
                            .join("");
                        frappe.msgprint({
                            title: __("Some invoices were not submitted"),
                            indicator: "orange",
                            message: `<ul>${details}</ul>`,
                        });
                    }

                    listview.refresh();
                },
            });
        }
    );
}
