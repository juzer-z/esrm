frappe.query_reports["Ticket Sales and Collection Summary"] = {
    filters: [
        {
            fieldname: "based_on",
            label: __("Summarize By"),
            fieldtype: "Select",
            options: "Customer\nReference\nBooking Owner\nAirline\nPayment Mode",
            default: "Customer",
            reqd: 1,
        },
        {
            fieldname: "from_date",
            label: __("Issue Date From"),
            fieldtype: "Date",
        },
        {
            fieldname: "to_date",
            label: __("Issue Date To"),
            fieldtype: "Date",
        },
        {
            fieldname: "approval_status",
            label: __("Approval Status"),
            fieldtype: "Select",
            options: "\nDraft\nPending Approval\nApproved\nRejected",
        },
        {
            fieldname: "status",
            label: __("Booking Status"),
            fieldtype: "Select",
            options: "\nDraft\nTicketed\nInvoiced\nPartially Paid\nPaid\nTravelled\nRefunded\nCancelled",
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
        {
            fieldname: "reference",
            label: __("Reference"),
            fieldtype: "Data",
        },
        {
            fieldname: "booking_owner",
            label: __("Booking Owner"),
            fieldtype: "Link",
            options: "User",
        },
    ],
};
