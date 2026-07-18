from pathlib import Path
from shutil import copyfile

import frappe


def apply_branding():
    source_logo = Path(frappe.get_app_path("esrm_travel", "public", "images", "esrm-logo.svg"))
    target_logo = Path.cwd() / "sites" / "assets" / "erpnext" / "images" / "erpnext-logo.svg"

    if not source_logo.exists():
        frappe.log_error(f"ESRM logo source not found: {source_logo}", "ESRM Branding")
        return

    target_logo.parent.mkdir(parents=True, exist_ok=True)
    copyfile(source_logo, target_logo)
