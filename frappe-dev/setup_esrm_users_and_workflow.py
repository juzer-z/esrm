import os

import frappe


SITE_NAME = "development.localhost"
BENCH_SITES_PATH = "/workspace/frappe-dev/frappe-bench/sites"


def ensure_module_profile():
    profile_name = "ESRM Ticketing Agent"
    blocked_modules = [
        "Accounting",
        "Accounts",
        "Assets",
        "Bulk Transaction",
        "Buying",
        "CRM",
        "Communication",
        "ERPNext Integrations",
        "ERPNext Settings",
        "Integrations",
        "Maintenance",
        "Manufacturing",
        "Portal",
        "Projects",
        "Quality Management",
        "Regional",
        "Selling",
        "Stock",
        "Subcontracting",
        "Support",
        "Telephony",
        "Tools",
        "Users",
        "Website",
    ]

    if frappe.db.exists("Module Profile", profile_name):
        profile = frappe.get_doc("Module Profile", profile_name)
    else:
        profile = frappe.new_doc("Module Profile")
        profile.module_profile_name = profile_name

    current = {row.module for row in profile.get("block_modules", [])}
    for module_name in blocked_modules:
        if module_name not in current:
            row = profile.append("block_modules", {})
            row.module = module_name

    profile.save(ignore_permissions=True)
    return profile_name


def set_workspace_roles(workspace_name, roles):
    workspace = frappe.get_doc("Workspace", workspace_name)
    workspace.set("roles", [])
    for role in roles:
        workspace.append("roles", {"role": role})
    workspace.save(ignore_permissions=True)


def ensure_workspace_visibility():
    admin_only_workspaces = [
        "Home",
        "Accounting",
        "Selling",
        "CRM",
        "Users",
        "Tools",
        "ERPNext Settings",
    ]
    for workspace_name in admin_only_workspaces:
        if frappe.db.exists("Workspace", workspace_name):
            set_workspace_roles(workspace_name, ["System Manager"])

    if frappe.db.exists("Workspace", "ESRM Travel"):
        set_workspace_roles("ESRM Travel", ["System Manager", "Ticketing Agent"])


def ensure_user(email, first_name, roles, module_profile, password):
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
    else:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name,
                "user_type": "System User",
                "send_welcome_email": 0,
                "enabled": 1,
            }
        )
        user.insert(ignore_permissions=True)

    user.first_name = first_name
    user.user_type = "System User"
    user.module_profile = module_profile
    user.enabled = 1

    existing_roles = {row.role for row in user.roles}
    desired_roles = set(roles)

    for role_name in desired_roles - existing_roles:
        user.append("roles", {"role": role_name})

    for row in list(user.roles):
        if row.role not in desired_roles and row.role not in {"All", "Desk User"}:
            user.roles.remove(row)

    user.save(ignore_permissions=True)
    user.new_password = password
    user.save(ignore_permissions=True)


def disable_sample_users():
    for email in ["accounts@esrm.local", "ticketing@esrm.local"]:
        if frappe.db.exists("User", email):
            user = frappe.get_doc("User", email)
            user.enabled = 0
            user.save(ignore_permissions=True)


def ensure_customer_permission():
    role = "Ticketing Agent"
    for permlevel in [0]:
        if frappe.db.exists(
            "Custom DocPerm",
            {
                "parent": "Customer",
                "role": role,
                "permlevel": permlevel,
            },
        ):
            continue

        docperm = frappe.get_doc(
            {
                "doctype": "Custom DocPerm",
                "parent": "Customer",
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "permlevel": permlevel,
                "select": 1,
                "read": 1,
                "write": 1,
                "create": 1,
                "print": 1,
                "email": 1,
                "report": 1,
                "export": 1,
            }
        )
        docperm.insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Customer")


def ensure_workflow():
    workflow_name = "Ticket Booking Approval"

    for state_name, style in [
        ("Draft", "Warning"),
        ("Pending Approval", "Primary"),
        ("Approved", "Success"),
        ("Rejected", "Danger"),
    ]:
        if not frappe.db.exists("Workflow State", state_name):
            doc = frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state_name, "style": style})
            doc.insert(ignore_permissions=True)

    for action_name in ["Submit for Approval", "Approve", "Reject", "Resubmit"]:
        if not frappe.db.exists("Workflow Action Master", action_name):
            doc = frappe.get_doc(
                {"doctype": "Workflow Action Master", "workflow_action_name": action_name}
            )
            doc.insert(ignore_permissions=True)

    if frappe.db.exists("Workflow", workflow_name):
        workflow = frappe.get_doc("Workflow", workflow_name)
        workflow.is_active = 0
        workflow.save(ignore_permissions=True)
        frappe.delete_doc("Workflow", workflow_name, ignore_permissions=True, force=1)

    workflow = frappe.get_doc(
        {
            "doctype": "Workflow",
            "workflow_name": workflow_name,
            "document_type": "Ticket Booking",
            "workflow_state_field": "approval_status",
            "is_active": 1,
            "override_status": 0,
            "send_email_alert": 0,
            "states": [
                {
                    "state": "Draft",
                    "doc_status": 0,
                    "allow_edit": "Ticketing Agent",
                    "avoid_status_override": 1,
                },
                {
                    "state": "Pending Approval",
                    "doc_status": 0,
                    "allow_edit": "System Manager",
                    "avoid_status_override": 1,
                },
                {
                    "state": "Approved",
                    "doc_status": 0,
                    "allow_edit": "System Manager",
                    "avoid_status_override": 1,
                },
                {
                    "state": "Rejected",
                    "doc_status": 0,
                    "allow_edit": "Ticketing Agent",
                    "avoid_status_override": 1,
                },
            ],
            "transitions": [
                {
                    "state": "Draft",
                    "action": "Submit for Approval",
                    "next_state": "Pending Approval",
                    "allowed": "Ticketing Agent",
                    "allow_self_approval": 1,
                },
                {
                    "state": "Pending Approval",
                    "action": "Approve",
                    "next_state": "Approved",
                    "allowed": "System Manager",
                    "allow_self_approval": 1,
                },
                {
                    "state": "Pending Approval",
                    "action": "Reject",
                    "next_state": "Rejected",
                    "allowed": "System Manager",
                    "allow_self_approval": 1,
                },
                {
                    "state": "Rejected",
                    "action": "Resubmit",
                    "next_state": "Pending Approval",
                    "allowed": "Ticketing Agent",
                    "allow_self_approval": 1,
                },
            ],
        }
    )
    workflow.insert(ignore_permissions=True)


def main():
    os.chdir(BENCH_SITES_PATH)
    frappe.init(site=SITE_NAME)
    frappe.connect()

    profile_name = ensure_module_profile()
    ensure_workspace_visibility()
    ensure_customer_permission()
    ensure_workflow()
    administrator = frappe.get_doc("User", "Administrator")
    administrator.module_profile = None
    administrator.save(ignore_permissions=True)
    ensure_user(
        email="agent@esrm.local",
        first_name="Agent",
        roles=["Ticketing Agent"],
        module_profile=profile_name,
        password="Agent#2026!",
    )
    disable_sample_users()

    frappe.db.commit()
    print("Provisioned module profile, workflow, and agent user.")
    frappe.destroy()


if __name__ == "__main__":
    main()
