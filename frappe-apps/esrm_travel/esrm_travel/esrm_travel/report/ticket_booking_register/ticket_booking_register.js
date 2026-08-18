frappe.query_reports["Ticket Booking Register"] = {
    filters: [
        {
            fieldname: "service_type",
            label: __("Service Type"),
            fieldtype: "Select",
            options: "\nTicket\nVisa",
        },
        {
            fieldname: "search",
            label: __("Search"),
            fieldtype: "Data",
            description: __("Ticket, passport, invoice, customer, passenger/applicant, destination, or reference"),
        },
        {
            fieldname: "from_date",
            label: __("Entry Date From"),
            fieldtype: "Date",
        },
        {
            fieldname: "to_date",
            label: __("Entry Date To"),
            fieldtype: "Date",
        },
        {
            fieldname: "flight_from_date",
            label: __("Travel Date From"),
            fieldtype: "Date",
        },
        {
            fieldname: "flight_to_date",
            label: __("Travel Date To"),
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
            fieldname: "destination_country",
            label: __("Visa Destination"),
            fieldtype: "Link",
            options: "Country",
        },
        {
            fieldname: "booking_owner",
            label: __("Service Owner"),
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
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nTicketed\nInvoiced\nPartially Paid\nPaid\nTravelled\nCompleted\nCancelled\nRefunded",
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
