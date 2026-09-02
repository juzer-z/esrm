import frappe
from frappe.utils import flt


def execute():
    if not frappe.db.table_exists("IATA Memo"):
        return
    for name in frappe.get_all("IATA Settlement", filters={"docstatus": 0}, pluck="name"):
        settlement = frappe.get_doc("IATA Settlement", name)
        for legacy in list(settlement.get("memos") or []):
            memo_name = frappe.db.get_value(
                "IATA Memo",
                {"memo_type": legacy.memo_type, "memo_number": legacy.memo_number},
                "name",
            )
            if not memo_name:
                memo = frappe.get_doc({
                    "doctype": "IATA Memo",
                    "company": settlement.company,
                    "memo_type": legacy.memo_type,
                    "memo_number": legacy.memo_number,
                    "memo_date": legacy.memo_date,
                    "airline_code": legacy.airline_code,
                    "travel_type": "International",
                    "amount": legacy.amount,
                    "attachment": legacy.attachment,
                    "remarks": legacy.remarks,
                })
                memo.insert(ignore_permissions=True)
                memo.submit()
        settlement.set("memos", [])
        if (
            not settlement.get("deposits")
            and flt(settlement.deposit_amount) > 0
            and settlement.deposit_date
            and settlement.reference_no
            and settlement.source_account
            and settlement.deposit_slip
        ):
            settlement.append("deposits", {
                "deposit_date": settlement.deposit_date,
                "reference_no": settlement.reference_no,
                "source_account": settlement.source_account,
                "amount": settlement.deposit_amount,
                "deposit_slip": settlement.deposit_slip,
            })
        settlement.save(ignore_permissions=True)
