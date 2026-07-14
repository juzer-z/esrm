frappe.query_reports["Pending Ticket Approvals"] = {
    filters: [
        {
            fieldname: "approval_status",
            label: __("Approval Status"),
            fieldtype: "Select",
            options: "\nPending Approval\nRejected\nDraft\nApproved",
            default: "Pending Approval",
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
        {
            fieldname: "booking_owner",
            label: __("Booking Owner"),
            fieldtype: "Link",
            options: "User",
        },
        {
            fieldname: "airline",
            label: __("Airline"),
            fieldtype: "Data",
        },
        {
            fieldname: "flight_from_date",
            label: __("Flight Date From"),
            fieldtype: "Date",
        },
        {
            fieldname: "flight_to_date",
            label: __("Flight Date To"),
            fieldtype: "Date",
        },
    ],
};
