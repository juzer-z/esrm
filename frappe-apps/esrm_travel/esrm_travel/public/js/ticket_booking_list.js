frappe.listview_settings["Ticket Booking"] = {
    onload(listview) {
        if (frappe.session.user !== "Administrator") return;

        listview.page.add_actions_menu_item(__("Approve Selected"), () => {
            const selected = listview.get_checked_items();
            if (!selected.length) {
                frappe.msgprint(__("Select at least one pending booking."));
                return;
            }

            frappe.confirm(
                __("Approve {0} selected booking(s)?", [selected.length]),
                () => {
                    frappe.call({
                        method: "esrm_travel.ticket_reissue.bulk_approve_pending_bookings",
                        args: { booking_names: selected.map((row) => row.name) },
                        freeze: true,
                        freeze_message: __("Approving selected bookings..."),
                        callback(response) {
                            const result = response.message || {};
                            const approved = result.approved || [];
                            const failed = result.failed || [];
                            if (failed.length) {
                                const details = failed
                                    .map((row) => `${frappe.utils.escape_html(row.booking)}: ${frappe.utils.escape_html(row.error)}`)
                                    .join("<br>");
                                frappe.msgprint({
                                    title: __("Approval completed with errors"),
                                    message: __("Approved: {0}<br><br>{1}", [approved.length, details]),
                                    indicator: "orange",
                                });
                            } else {
                                frappe.show_alert({
                                    message: __("Approved {0} booking(s)", [approved.length]),
                                    indicator: "green",
                                });
                            }
                            listview.refresh();
                        },
                    });
                }
            );
        });
    },
};
