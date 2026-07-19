frappe.listview_settings["Ticket Booking"] = {
    onload(listview) {
        listview.page.add_actions_menu_item(__("Create Sales Invoice"), () => {
            const selected = listview.get_checked_items();

            if (!selected.length) {
                frappe.msgprint(__("Select one or more approved ticket bookings first."));
                return;
            }

            frappe.call({
                method: "esrm_travel.esrm_travel.doctype.ticket_booking.ticket_booking.make_group_sales_invoice",
                args: {
                    bookings: selected.map((row) => row.name),
                },
                freeze: true,
                freeze_message: __("Creating Sales Invoice..."),
                callback: (r) => {
                    if (r.message) {
                        frappe.show_alert({
                            message: __("Sales Invoice {0} created", [r.message]),
                            indicator: "green",
                        });
                        frappe.set_route("Form", "Sales Invoice", r.message);
                    }
                },
            });
        });
    },
};
