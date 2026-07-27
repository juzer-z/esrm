(() => {
    const POLL_INTERVAL_MS = 10000;
    let latestNotificationName = null;
    let pollingStarted = false;
    let profitCardObserver = null;

    function getNotificationView() {
        return frappe.frappe_toolbar && frappe.frappe_toolbar.notifications;
    }

    async function refreshIfNew() {
        if (document.hidden || frappe.session.user === "Guest") {
            return;
        }

        const view = getNotificationView();
        if (!view) {
            return;
        }

        try {
            const response = await view.get_notifications_list(view.max_length);
            if (!response.message) {
                return;
            }

            const items = response.message.notification_logs || [];
            const newestName = items[0] && items[0].name;

            if (latestNotificationName === null) {
                latestNotificationName = newestName || "";
                return;
            }
            if (!newestName || newestName === latestNotificationName) {
                return;
            }

            latestNotificationName = newestName;
            view.dropdown_items = items;
            frappe.update_user_info(response.message.user_info);
            view.render_notifications_dropdown();
            view.toggle_notification_icon(false);
        } catch (error) {
            // A temporary connection failure should not interrupt Desk usage.
        }
    }

    function startPolling() {
        if (pollingStarted || !getNotificationView()) {
            return;
        }

        pollingStarted = true;
        refreshIfNew();
        window.setInterval(refreshIfNew, POLL_INTERVAL_MS);
        document.addEventListener("visibilitychange", () => {
            if (!document.hidden) {
                refreshIfNew();
            }
        });
    }

    function removeProfitCardForNonAdministrator() {
        if (frappe.session.user === "Administrator") {
            return;
        }

        const route = frappe.get_route();
        if (route[0] !== "Workspaces" || route[1] !== "ESRM") {
            return;
        }

        document
            .querySelectorAll('.widget[data-widget-name="Profit"]')
            .forEach((widget) => (widget.closest(".ce-block") || widget).remove());
    }

    function watchProfitCardVisibility() {
        if (frappe.session.user === "Administrator" || profitCardObserver) {
            return;
        }

        profitCardObserver = new MutationObserver(removeProfitCardForNonAdministrator);
        profitCardObserver.observe(document.body, { childList: true, subtree: true });
        removeProfitCardForNonAdministrator();
    }

    $(document).on("toolbar_setup", startPolling);
    $(document).on("page-change", () => {
        window.setTimeout(removeProfitCardForNonAdministrator, 0);
    });
    $(startPolling);
    $(watchProfitCardVisibility);
})();
