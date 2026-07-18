from pathlib import Path
from shutil import copyfile

import frappe
from frappe.utils import get_bench_path


def apply_branding():
    source_logo = Path(frappe.get_app_path("esrm_travel", "public", "images", "esrm-logo.svg"))

    if not source_logo.exists():
        frappe.log_error(f"ESRM logo source not found: {source_logo}", "ESRM Branding")
        return

    bench_path = Path(get_bench_path())
    targets = [
        bench_path / "sites" / "assets" / "erpnext" / "images" / "erpnext-logo.svg",
        bench_path / "sites" / "assets" / "erpnext" / "images" / "erpnext-favicon.svg",
        bench_path / "sites" / "assets" / "frappe" / "images" / "frappe-favicon.svg",
    ]

    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        copyfile(source_logo, target)
