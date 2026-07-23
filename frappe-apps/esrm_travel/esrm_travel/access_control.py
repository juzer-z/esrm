import frappe
from werkzeug.exceptions import HTTPException
from werkzeug.utils import redirect


AGENT_USER = "agent@esrm.local"
AGENT_ROLE = "ESRM Agent"
APPROVER_ROLE = "ESRM Approver"
ALLOWED_AGENT_MODULES = {
    "Accounts", "Communication", "Contacts", "Core", "Desk", "ESRM Travel",
    "Printing", "Selling", "Setup", "Utilities", "Workflow",
}

AGENT_PERMISSIONS = {
    "Ticket Booking": dict(
        read=1, write=1, create=1, submit=1, email=1, print=1, report=1, select=1
    ),
    "Ticket Sector": dict(read=1, write=1, create=1, select=1),
    "Customer": dict(read=1, write=1, create=1, print=1, report=1, select=1),
    "Sales Invoice": dict(read=1, write=1, create=1, email=1, print=1, report=1, select=1),
    "Payment Entry": dict(read=1, write=1, create=1, print=1, report=1, select=1),
    "Page": dict(read=1, select=1),
}


def redirect_agent_from_setup_wizard():
    request = getattr(frappe.local, "request", None)
    if (
        frappe.session.user == AGENT_USER
        and request
        and request.path.rstrip("/") == "/app/setup-wizard"
    ):
        raise HTTPException(response=redirect("/app/esrm", code=302))


def setup_access_controls():
    ensure_role(AGENT_ROLE)
    ensure_role(APPROVER_ROLE)
    configure_administrator()
    setup_agent_permissions()
    setup_workflow()
    if frappe.db.exists("User", AGENT_USER):
        configure_agent_user()
    frappe.clear_cache()


def ensure_role(role_name):
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
            ignore_permissions=True
        )


def setup_agent_permissions():
    for name in frappe.get_all("Custom DocPerm", filters={"role": AGENT_ROLE}, pluck="name"):
        frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True, force=True)

    permission_fields = (
        "read", "write", "create", "delete", "submit", "cancel", "amend", "report",
        "export", "import", "share", "print", "email", "select",
    )
    for doctype, allowed in AGENT_PERMISSIONS.items():
        values = {
            "doctype": "Custom DocPerm", "parent": doctype, "parenttype": "DocType",
            "parentfield": "permissions", "role": AGENT_ROLE, "permlevel": 0,
        }
        values.update({field: int(allowed.get(field, 0)) for field in permission_fields})
        frappe.get_doc(values).insert(ignore_permissions=True)
def setup_workflow():
    if not frappe.db.exists("Workflow", "Ticket Booking Approval"):
        return
    workflow = frappe.get_doc("Workflow", "Ticket Booking Approval")
    for state in workflow.states:
        if state.state in {"Pending Approval", "Approved"}:
            state.allow_edit = APPROVER_ROLE
        elif state.state in {"Draft", "Rejected"}:
            state.allow_edit = AGENT_ROLE
    for transition in workflow.transitions:
        if transition.action in {"Approve", "Reject"}:
            transition.allowed = APPROVER_ROLE
            transition.allow_self_approval = 0
        elif transition.action == "Send for Approval":
            transition.allowed = AGENT_ROLE
            # The booking owner must be able to send their own draft onward.
            # Final approval and rejection remain restricted to approvers above.
            transition.allow_self_approval = 1
    workflow.save(ignore_permissions=True)


def configure_administrator():
    if not frappe.db.exists("Has Role", {"parent": "Administrator", "role": APPROVER_ROLE}):
        frappe.get_doc(
            {
                "doctype": "Has Role", "parent": "Administrator", "parenttype": "User",
                "parentfield": "roles", "role": APPROVER_ROLE,
            }
        ).insert(ignore_permissions=True)


def configure_agent_user():
    user = frappe.get_doc("User", AGENT_USER)
    user.enabled = 1
    user.user_type = "System User"
    user.default_workspace = "ESRM"
    user.module_profile = None
    blocked = frappe.get_all(
        "Module Def", filters={"name": ["not in", sorted(ALLOWED_AGENT_MODULES)]},
        pluck="name", order_by="name",
    )
    user.set("block_modules", [{"module": module} for module in blocked])
    user.set("roles", [{"role": AGENT_ROLE}])
    user.save(ignore_permissions=True)
