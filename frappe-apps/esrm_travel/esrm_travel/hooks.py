from . import __version__ as app_version

app_name = "esrm_travel"
app_title = "ESRM"
app_publisher = "3J Technologies"
app_description = "Ticketing and operations for ERPNext"
app_email = "info@example.com"
app_license = "MIT"
app_icon = "fa fa-plane"
app_color = "#0b7285"
source_link = ""

jinja = {
    "methods": [
        "esrm_travel.print_formats.get_invoice_credit_summary",
    ],
}

app_include_js = ["/assets/esrm_travel/js/approval_notification_refresh.js?v=eb8affd"]

doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
}

doctype_list_js = {
    "Sales Invoice": "public/js/sales_invoice_list.js",
}

before_request = "esrm_travel.access_control.redirect_agent_from_setup_wizard"

after_migrate = "esrm_travel.dashboard.setup_workspace"

fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["Ticketing Agent", "Ticketing Manager", "ESRM Agent", "ESRM Approver"]]]},
    {"dt": "Workflow State", "filters": [["name", "in", ["Draft", "Pending Approval"]]]},
    {"dt": "Workflow Action Master", "filters": [["name", "in", ["Send for Approval"]]]},
    {"dt": "Workflow", "filters": [["name", "in", ["Ticket Booking Approval", "Visa Service Approval"]]]},
    {"dt": "Fiscal Year", "filters": [["name", "in", ["2026-2027"]]]},
    {"dt": "Custom DocPerm", "filters": [["role", "=", "ESRM Agent"]]},
    {
        "dt": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                [
                    "Customer-esrm_short_name",
                    "Customer-esrm_customer_code",
                    "Sales Invoice-esrm_invoice_number",
                    "Sales Invoice-esrm_ticket_booking",
                    "Sales Invoice-esrm_ticket_bookings",
                    "Sales Invoice-esrm_passenger_names",
                    "Sales Invoice-esrm_visa_service",
                    "Sales Invoice-esrm_visa_services",
                    "Sales Invoice-esrm_applicant_names",
                    "Payment Entry-esrm_ticket_booking",
                    "Employee-custom_national_id",
                    "Employee-custom_tin_number",
                ],
            ]
        ],
    },
]

doc_events = {
    "Notification Log": {
        "after_insert": "esrm_travel.notification_email.queue_notification_email",
    },
    "Ticket Booking": {
        "on_update": "esrm_travel.approval_notifications.notify_ticket_booking_approval",
        "on_update_after_submit": "esrm_travel.approval_notifications.notify_ticket_cost_entered",
    },
    "Visa Service": {
        "on_update": "esrm_travel.approval_notifications.notify_service_approval",
    },
    "Sales Invoice": {
        "before_validate": "esrm_travel.workflow.set_sales_invoice_search_names",
        "on_submit": "esrm_travel.workflow.on_submit_sales_invoice",
        "on_update_after_submit": "esrm_travel.workflow.on_update_after_submit_sales_invoice",
        "on_cancel": "esrm_travel.workflow.on_cancel_sales_invoice",
        "after_delete": "esrm_travel.workflow.after_delete_sales_invoice",
    },
    "Payment Entry": {
        "before_validate": "esrm_travel.workflow.before_validate_payment_entry",
        "on_submit": "esrm_travel.workflow.on_submit_payment_entry",
        "on_update_after_submit": "esrm_travel.workflow.on_update_after_submit_payment_entry",
        "on_cancel": "esrm_travel.workflow.on_cancel_payment_entry",
    },
}
