frappe.ui.form.on("Ticket Booking", {
    gross_amount(frm) {
        calculate_profitability(frm);
    },

    iata_amount(frm) {
        calculate_profitability(frm);
    },

    supplier_cost(frm) {
        calculate_profitability(frm);
    },

    invoice_amount(frm) {
        calculate_profitability(frm);
    },

    payment_mode(frm) {
        calculate_profitability(frm);
    },

    refresh(frm) {
        if (!frm.is_new() && !frm.doc.sales_invoice && frm.doc.approval_status === "Approved") {
            frm.add_custom_button(__("Create Sales Invoice"), () => {
                frappe.call({
                    method: "esrm_travel.esrm_travel.doctype.ticket_booking.ticket_booking.make_sales_invoice",
                    args: {
                        source_name: frm.doc.name,
                    },
                    freeze: true,
                    freeze_message: __("Creating Sales Invoice..."),
                    callback: (r) => {
                        if (r.message) {
                            frappe.show_alert({
                                message: __("Sales Invoice {0} created", [r.message]),
                                indicator: "green",
                            });
                            frm.reload_doc().then(() => {
                                frappe.set_route("Form", "Sales Invoice", r.message);
                            });
                        }
                    },
                });
            });
        }

        if (frm.doc.sales_invoice) {
            frm.add_custom_button(__("Open Sales Invoice"), () => {
                frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
            });
        }
    },
});

function calculate_profitability(frm) {
    const gross_amount = flt(frm.doc.gross_amount);
    const iata_amount = flt(frm.doc.iata_amount);
    const supplier_cost = flt(frm.doc.supplier_cost);
    const invoice_amount = flt(frm.doc.invoice_amount);

    if (frm.doc.payment_mode === "IATA") {
        frm.set_value("commission", gross_amount - iata_amount);
        frm.set_value("profit", invoice_amount - iata_amount);
    } else {
        frm.set_value("commission", 0);
        frm.set_value("profit", invoice_amount - supplier_cost);
    }

    frm.set_value("discount", gross_amount - invoice_amount);
}
