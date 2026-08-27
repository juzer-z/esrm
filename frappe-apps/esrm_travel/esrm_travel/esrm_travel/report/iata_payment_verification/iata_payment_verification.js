frappe.query_reports["IATA Payment Verification"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("Issue Date From"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.get_today(), -15),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("Issue Date To"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
    ],

    onload(report) {
        report.page.add_inner_button(__("Download Verified PDF"), () => {
            const filters = report.get_values();
            if (!filters.from_date || !filters.to_date) {
                frappe.msgprint(__("Please select both issue dates."));
                return;
            }

            const query = new URLSearchParams({
                from_date: filters.from_date,
                to_date: filters.to_date,
            });
            window.open(
                `/api/method/esrm_travel.esrm_travel.report.iata_payment_verification.iata_payment_verification.download_verified_pdf?${query.toString()}`,
                "_blank"
            );
        });
    },
};
