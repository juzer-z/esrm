frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (frappe.session.user !== "Administrator" || frm.is_new()) {
            return;
        }

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(
                __("Submit Invoice"),
                () => frm.savesubmit(),
                __("Actions")
            );
        }

        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(
                __("Cancel Invoice"),
                () => {
                    frappe.confirm(
                        __("Cancel Sales Invoice {0}? This will reverse its accounting entries.", [
                            frm.doc.name,
                        ]),
                        () => {
                            frappe.call({
                                method: "esrm_travel.workflow.cancel_sales_invoice",
                                args: { invoice_name: frm.doc.name },
                                freeze: true,
                                freeze_message: __("Cancelling Sales Invoice..."),
                                callback: (r) => {
                                    if (!r.exc) {
                                        frappe.show_alert({
                                            message: __("Sales Invoice {0} cancelled.", [
                                                frm.doc.name,
                                            ]),
                                            indicator: "green",
                                        });
                                        frm.reload_doc();
                                    }
                                },
                            });
                        }
                    );
                },
                __("Actions")
            );
        }

        if (frm.doc.docstatus === 2) {
            frm.add_custom_button(
                __("Delete Cancelled Invoice"),
                () => {
                    frappe.confirm(
                        __("Permanently delete cancelled Sales Invoice {0}? ERPNext will block deletion if another document still depends on it.", [
                            frm.doc.name,
                        ]),
                        () => {
                            frappe.call({
                                method: "frappe.client.delete",
                                args: {
                                    doctype: "Sales Invoice",
                                    name: frm.doc.name,
                                },
                                freeze: true,
                                freeze_message: __("Deleting Cancelled Invoice..."),
                                callback: () => {
                                    frappe.show_alert({
                                        message: __("Cancelled Sales Invoice deleted."),
                                        indicator: "green",
                                    });
                                    frappe.set_route("List", "Sales Invoice");
                                },
                            });
                        }
                    );
                },
                __("Actions")
            );
        }
    },
});
