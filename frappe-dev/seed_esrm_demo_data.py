import os

import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import add_days, getdate, nowdate
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from esrm_travel.esrm_travel.doctype.ticket_booking.ticket_booking import make_sales_invoice


SITE_NAME = "development.localhost"
BENCH_SITES_PATH = "/workspace/frappe-dev/frappe-bench/sites"


CUSTOMERS = [
    "ABC Holdings Ltd",
    "North Star Traders",
    "Sky Bridge Limited",
    "Meridian Ventures",
    "Horizon Fabrics",
]


BOOKINGS = [
    {
        "passenger_name": "Salman Hossain",
        "pnr": "DEM101",
        "customer": "Sky Bridge Limited",
        "airline": "Biman Bangladesh",
        "days_from_today": 3,
        "payment_mode": "Cash",
        "gross_amount": 32000,
        "supplier_cost": 27500,
        "invoice_amount": 32000,
        "approval_flow": "pending",
    },
    {
        "passenger_name": "Nadia Karim",
        "pnr": "DEM102",
        "customer": "Meridian Ventures",
        "airline": "US-Bangla",
        "days_from_today": 5,
        "payment_mode": "Bank Transfer",
        "gross_amount": 41000,
        "supplier_cost": 35500,
        "invoice_amount": 41000,
        "approval_flow": "approved",
    },
    {
        "passenger_name": "Rafi Ahmed",
        "pnr": "DEM103",
        "customer": "Horizon Fabrics",
        "airline": "Qatar Airways",
        "days_from_today": 8,
        "payment_mode": "Card",
        "gross_amount": 125000,
        "supplier_cost": 113000,
        "invoice_amount": 125000,
        "approval_flow": "rejected",
    },
    {
        "passenger_name": "Maliha Sultana",
        "pnr": "DEM104",
        "customer": "ABC Holdings Ltd",
        "airline": "Emirates",
        "days_from_today": 11,
        "payment_mode": "Bank Transfer",
        "gross_amount": 138000,
        "supplier_cost": 126000,
        "invoice_amount": 138000,
        "approval_flow": "invoice_draft",
    },
    {
        "passenger_name": "Tanvir Hasan",
        "pnr": "DEM105",
        "customer": "North Star Traders",
        "airline": "FlyDubai",
        "days_from_today": 13,
        "payment_mode": "Cash",
        "gross_amount": 54000,
        "supplier_cost": 47000,
        "invoice_amount": 54000,
        "approval_flow": "unpaid",
    },
    {
        "passenger_name": "Rumana Akter",
        "pnr": "DEM106",
        "customer": "Sky Bridge Limited",
        "airline": "Air Arabia",
        "days_from_today": 16,
        "payment_mode": "Cash",
        "gross_amount": 48500,
        "supplier_cost": 42000,
        "invoice_amount": 48500,
        "approval_flow": "partial",
        "collection_amount": 20000,
    },
    {
        "passenger_name": "Imran Chowdhury",
        "pnr": "DEM107",
        "customer": "Meridian Ventures",
        "airline": "Singapore Airlines",
        "days_from_today": 18,
        "payment_mode": "Bank Transfer",
        "gross_amount": 172000,
        "supplier_cost": 158500,
        "invoice_amount": 172000,
        "approval_flow": "paid",
    },
    {
        "passenger_name": "Sharmin Nahar",
        "pnr": "DEM108",
        "customer": "Horizon Fabrics",
        "airline": "Thai Airways",
        "days_from_today": 21,
        "payment_mode": "Card",
        "gross_amount": 98000,
        "supplier_cost": 90500,
        "invoice_amount": 98000,
        "approval_flow": "paid",
    },
]


def ensure_customer(name):
    if frappe.db.exists("Customer", name):
        return name

    doc = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": name,
            "customer_group": "Commercial",
            "territory": "All Territories",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def create_booking(entry):
    frappe.set_user("agent@esrm.local")
    booking = frappe.get_doc(
        {
            "doctype": "Ticket Booking",
            "customer": entry["customer"],
            "issue_date": nowdate(),
            "passenger_name": entry["passenger_name"],
            "pnr": entry["pnr"],
            "airline": entry["airline"],
            "flight_date": add_days(nowdate(), entry["days_from_today"]),
            "payment_mode": entry["payment_mode"],
            "gross_amount": entry["gross_amount"],
            "supplier_cost": entry["supplier_cost"],
            "invoice_amount": entry["invoice_amount"],
            "remarks": f"Seeded demo booking for {entry['approval_flow']}",
            "sectors": [
                {
                    "origin": "DAC",
                    "destination": "DXB" if entry["days_from_today"] % 2 == 0 else "CGP",
                    "flight_number": f"FL{entry['days_from_today']}",
                }
            ],
        }
    )
    booking.insert(ignore_permissions=False)
    return booking


def submit_for_approval(booking):
    frappe.set_user("agent@esrm.local")
    booking = frappe.get_doc("Ticket Booking", booking.name)
    booking = apply_workflow(booking, "Submit for Approval")
    return booking


def approve_or_reject(booking, final_state):
    frappe.set_user("Administrator")
    booking = frappe.get_doc("Ticket Booking", booking.name)
    if final_state == "rejected":
        booking = apply_workflow(booking, "Reject")
    else:
        booking = apply_workflow(booking, "Approve")
    return booking


def create_payment(invoice_name, amount):
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    payment_entry = get_payment_entry("Sales Invoice", invoice.name, party_amount=amount)
    payment_entry.reference_no = f"SEED-{invoice.name}"
    payment_entry.reference_date = getdate(nowdate())
    if payment_entry.references:
        payment_entry.references[0].allocated_amount = amount
    payment_entry.paid_amount = amount
    payment_entry.received_amount = amount
    payment_entry.insert(ignore_permissions=True)
    payment_entry.submit()
    return payment_entry.name


def build_dataset():
    results = []

    for customer in CUSTOMERS:
        ensure_customer(customer)

    for entry in BOOKINGS:
        if frappe.db.exists("Ticket Booking", {"pnr": entry["pnr"]}):
            continue

        booking = create_booking(entry)
        flow = entry["approval_flow"]

        if flow == "pending":
            submit_for_approval(booking)

        elif flow == "rejected":
            booking = submit_for_approval(booking)
            approve_or_reject(booking, "rejected")

        else:
            booking = submit_for_approval(booking)
            approve_or_reject(booking, "approved")
            frappe.set_user("Administrator")
            invoice_name = make_sales_invoice(booking.name)

            if flow in {"unpaid", "partial", "paid"}:
                invoice = frappe.get_doc("Sales Invoice", invoice_name)
                invoice.submit()

                if flow == "partial":
                    create_payment(invoice_name, entry["collection_amount"])
                elif flow == "paid":
                    create_payment(invoice_name, invoice.grand_total)

        results.append(entry["pnr"])

    frappe.db.commit()
    return results


def main():
    os.chdir(BENCH_SITES_PATH)
    frappe.init(site=SITE_NAME)
    frappe.connect()
    created = build_dataset()
    print({"created_or_processed": created})
    frappe.destroy()


if __name__ == "__main__":
    main()
