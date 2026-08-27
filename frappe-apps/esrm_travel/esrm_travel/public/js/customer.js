frappe.ui.form.on("Customer", {
    refresh(frm) {
        if (
            frappe.session.user !== "Administrator" ||
            frm.is_new() ||
            frm.doc.__islocal
        ) {
            return;
        }

        frm.add_custom_button(
            __("Delete Customer"),
            () => {
                frappe.confirm(
                    __("Permanently delete customer {0}? ERPNext will block deletion if accounting or operational records are linked.", [
                        frm.doc.name,
                    ]),
                    () => {
                        frappe.call({
                            method: "frappe.client.delete",
                            args: {
                                doctype: "Customer",
                                name: frm.doc.name,
                            },
                            freeze: true,
                            freeze_message: __("Deleting Customer..."),
                            callback: () => {
                                frappe.show_alert({
                                    message: __("Customer deleted."),
                                    indicator: "green",
                                });
                                frappe.set_route("List", "Customer");
                            },
                        });
                    }
                );
            },
            __("Actions")
        );
    },
});
