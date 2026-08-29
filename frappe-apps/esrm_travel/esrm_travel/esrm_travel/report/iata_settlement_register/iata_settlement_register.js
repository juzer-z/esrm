frappe.query_reports["IATA Settlement Register"] = {
    filters: [
        { fieldname: "from_date", label: __("Deposit Date From"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -1) },
        { fieldname: "to_date", label: __("Deposit Date To"), fieldtype: "Date", default: frappe.datetime.get_today() },
        { fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nDraft\nSubmitted\nCancelled" },
        { fieldname: "source_account", label: __("Paid From"), fieldtype: "Link", options: "Account" },
    ],
};
