frappe.query_reports["Cash Advance Register"] = {
    filters: [
        { fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.nowdate(), -1) },
        { fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.nowdate() },
        { fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
        { fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nDraft\nPending Approval\nApproved - Awaiting Disbursement\nPartially Disbursed\nDisbursed\nCash Return Due\nSettled\nOverdue\nCancelled" },
    ],
};
