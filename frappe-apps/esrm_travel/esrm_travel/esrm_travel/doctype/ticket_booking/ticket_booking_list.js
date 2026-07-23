frappe.listview_settings["Ticket Booking"] = {
    onload(listview) {
        bind_refreshing_workflow_actions(listview);

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

function bind_refreshing_workflow_actions(listview) {
    // Frappe v15's standard bulk workflow handler does not refresh the List
    // View after the server updates the documents. Replace only this DocType's
    // workflow menu handlers so the new states appear immediately.
    setTimeout(() => {
        Object.entries(listview.workflow_action_items || {}).forEach(([action, $item]) => {
            $item.off("click").on("click.esrm_workflow_refresh", async (event) => {
                event.preventDefault();
                event.stopImmediatePropagation();

                if ($item.hasClass("disabled")) {
                    return;
                }

                const docnames = listview.get_checked_items(true);
                if (!docnames.length) {
                    return;
                }

                listview.disable_list_update = true;
                frappe.dom.freeze(__("Updating ticket bookings..."));

                try {
                    await frappe.xcall("frappe.model.workflow.bulk_workflow_approval", {
                        docnames,
                        doctype: listview.doctype,
                        action,
                    });
                    listview.disable_list_update = false;
                    listview.clear_checked_items();
                    await listview.refresh();
                } finally {
                    listview.disable_list_update = false;
                    frappe.dom.unfreeze();
                }
            });
        });
    }, 0);
}
