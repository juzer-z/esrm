frappe.ui.form.on("Visa Service", {
    refresh(frm) {
        frm.set_query("service_package", () => ({ filters: { active: 1 } }));
        const can_reassign_owner = frappe.session.user === "Administrator";
        frm.set_df_property("service_owner", "read_only", !can_reassign_owner);
        if (frm.is_new() && !frm.doc.service_owner) {
            frm.set_value("service_owner", frappe.session.user);
        }

        if (
            !frm.is_new()
            && frm.doc.docstatus === 1
            && frm.doc.approval_status === "Approved"
            && !frm.doc.sales_invoice
        ) {
            frm.add_custom_button(
                __("Create Sales Invoice"),
                () => {
                    frappe.call({
                        method: "esrm_travel.esrm_travel.doctype.visa_service.visa_service.make_sales_invoice",
                        args: { source_name: frm.doc.name },
                        freeze: true,
                        freeze_message: __("Creating Sales Invoice..."),
                        callback: (r) => {
                            if (r.message) {
                                frappe.set_route("Form", "Sales Invoice", r.message);
                            }
                        },
                    });
                },
                __("Actions")
            );
        }
    },

    service_package(frm) {
        if (!frm.doc.service_package) {
            return;
        }
        frappe.call({
            method: "esrm_travel.esrm_travel.doctype.visa_service.visa_service.get_package_defaults",
            args: { package_name: frm.doc.service_package },
            callback: (r) => {
                if (!r.message) {
                    return;
                }
                const values = r.message;
                const documents = values.documents || [];
                delete values.documents;
                Object.entries(values).forEach(([fieldname, value]) => frm.set_value(fieldname, value));
                frm.clear_table("documents");
                documents.forEach((document_type) => {
                    const row = frm.add_child("documents");
                    row.document_type = document_type;
                    row.required = 1;
                });
                frm.refresh_field("documents");
                calculate_amounts(frm);
            },
        });
    },

    government_fee: calculate_amounts,
    service_charge: calculate_amounts,
    other_charges: calculate_amounts,
    discount: calculate_amounts,
    supplier_cost: calculate_amounts,
});

frappe.ui.form.on("Visa Document Checklist Item", {
    received(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.received && !row.received_date) {
            frappe.model.set_value(cdt, cdn, "received_date", frappe.datetime.get_today());
        }
    },
    verified(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.verified && !row.received) {
            frappe.model.set_value(cdt, cdn, "received", 1);
        }
    },
});

function calculate_amounts(frm) {
    const invoice_amount = Math.max(
        flt(frm.doc.government_fee)
        + flt(frm.doc.service_charge)
        + flt(frm.doc.other_charges)
        - flt(frm.doc.discount),
        0
    );
    frm.set_value("invoice_amount", invoice_amount);
    frm.set_value("total_cost", flt(frm.doc.supplier_cost));
    frm.set_value("profit", invoice_amount - flt(frm.doc.supplier_cost));
}
