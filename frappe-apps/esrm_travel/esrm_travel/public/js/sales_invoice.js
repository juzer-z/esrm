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
                        () => frm.savecancel()
                    );
                },
                __("Actions")
            );
        }
    },
});
