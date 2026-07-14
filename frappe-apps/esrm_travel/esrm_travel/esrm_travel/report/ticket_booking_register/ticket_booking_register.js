frappe.query_reports["Ticket Booking Register"] = {
    filters: [
        {
            fieldname: "search",
            label: __("Search"),
            fieldtype: "Data",
            description: __("Ticket Number, Invoice Number, Customer, Passenger, or Reference"),
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
            fieldname: "flight_from_date",
            label: __("Flight Date From"),
            fieldtype: "Date",
        },
        {
            fieldname: "flight_to_date",
            label: __("Flight Date To"),
            fieldtype: "Date",
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
            fieldname: "airline",
            label: __("Airline"),
            fieldtype: "Data",
        },
        {
            fieldname: "booking_owner",
            label: __("Booking Owner"),
            fieldtype: "Link",
            options: "User",
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
            fieldname: "invoice_status",
            label: __("Invoice Status"),
            fieldtype: "Select",
            options: "\nNot Invoiced\nDraft\nUnpaid\nOverdue\nPartly Paid\nPaid\nCancelled\nCredit Note Issued",
        },
        {
            fieldname: "payment_mode",
            label: __("Payment Mode"),
            fieldtype: "Select",
            options: "\nIATA\nNon-IATA\nCard\nCash\nBank Transfer",
        },
    ],
};
