frappe.listview_settings["Visa Service"] = {
    onload(listview) {
        listview.page.add_action_item(__("Create Sales Invoice"), () => {
            const selected = listview.get_checked_items();
            if (!selected.length) {
                frappe.msgprint(__("Select at least one Visa Service."));
                return;
            }
            frappe.call({
                method: "esrm_travel.esrm_travel.doctype.visa_service.visa_service.make_group_sales_invoice",
                args: { services: selected.map((row) => row.name) },
                freeze: true,
                freeze_message: __("Creating Sales Invoice..."),
                callback: (r) => {
                    if (r.message) {
                        frappe.set_route("Form", "Sales Invoice", r.message);
                    }
                },
            });
        });
    },
};
