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

after_migrate = "esrm_travel.dashboard.setup_workspace"

fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["Ticketing Agent", "Ticketing Manager", "ESRM Agent"]]]},
    {"dt": "Workflow State", "filters": [["name", "in", ["Draft", "Pending Approval"]]]},
    {"dt": "Workflow Action Master", "filters": [["name", "in", ["Send for Approval"]]]},
    {"dt": "Workflow", "filters": [["name", "in", ["Ticket Booking Approval"]]]},
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
                    "Payment Entry-esrm_ticket_booking",
                ],
            ]
        ],
    },
]

doc_events = {
    "Sales Invoice": {
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
