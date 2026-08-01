frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (
            frappe.session.user !== "Administrator"
            || frm.is_new()
            || frm.doc.docstatus !== 0
        ) {
            return;
        }

        frm.add_custom_button(
            __("Submit Invoice"),
            () => frm.savesubmit(),
            __("Actions")
        );
    },
});
