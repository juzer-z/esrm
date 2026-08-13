import frappe


def execute():
    for invoice_name in frappe.get_all("Sales Invoice", pluck="name"):
        passenger_names = []
        rows = frappe.get_all(
            "ESRM Invoice Ticket",
            filters={"parent": invoice_name, "parenttype": "Sales Invoice"},
            fields=["passenger_name"],
            order_by="idx asc",
        )
        for row in rows:
            passenger_name = (row.passenger_name or "").strip()
            if passenger_name and passenger_name not in passenger_names:
                passenger_names.append(passenger_name)

        frappe.db.set_value(
            "Sales Invoice",
            invoice_name,
            "esrm_passenger_names",
            "\n".join(passenger_names),
            update_modified=False,
        )
