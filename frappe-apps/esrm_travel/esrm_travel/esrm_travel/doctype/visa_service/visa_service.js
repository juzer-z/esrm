frappe.ui.form.on("Visa Service", {
    refresh(frm) {
        frm.set_query("service_package", () => ({ filters: { active: 1 } }));
        const can_reassign_owner = frappe.session.user === "Administrator";
        frm.set_df_property("service_owner", "read_only", !can_reassign_owner);
        if (frm.is_new() && !frm.doc.service_owner) {
            frm.set_value("service_owner", frappe.session.user);
        }
        setup_administrator_invoice_amendment(frm);

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

        if (frm.doc.sales_invoice) {
            frm.add_custom_button(
                __("Open Sales Invoice"),
                () => frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice),
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

    customer(frm) {
        if (!frm.doc.customer) {
            return;
        }
        frappe.db.get_value("Customer", frm.doc.customer, "customer_name").then((r) => {
            const customer_name = r.message && r.message.customer_name;
            if (customer_name) {
                frm.set_value("applicant_name", customer_name);
            }
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

const VISA_INVOICE_AMENDMENT_FIELDS = [
    "customer",
    "reference",
    "invoice_number",
    "application_date",
    "purpose",
    "applicant_name",
    "passport_number",
    "service_package",
    "destination_country",
    "visa_category",
    "visa_type",
    "processing_type",
    "number_of_entries",
    "intended_travel_date",
    "currency",
    "government_fee",
    "service_charge",
    "other_charges",
    "discount",
    "customer_remarks",
];

function setup_administrator_invoice_amendment(frm) {
    if (
        frm.is_new()
        || frm.doc.docstatus !== 1
        || frm.doc.approval_status !== "Approved"
    ) {
        return;
    }

    VISA_INVOICE_AMENDMENT_FIELDS.forEach((fieldname) => {
        frm.set_df_property(fieldname, "read_only", true);
    });
    frm.set_df_property("amendment_reason", "read_only", true);

    if (frappe.session.user !== "Administrator") {
        return;
    }

    frm.add_custom_button(
        __("Amend Approved Visa Service"),
        () => {
            frappe.prompt(
                [
                    {
                        fieldname: "reason",
                        fieldtype: "Small Text",
                        label: __("Amendment Reason"),
                        reqd: 1,
                    },
                ],
                (values) => {
                    frm.set_value("amendment_reason", values.reason).then(() => {
                        VISA_INVOICE_AMENDMENT_FIELDS.forEach((fieldname) => {
                            frm.set_df_property(fieldname, "read_only", false);
                        });
                        frappe.show_alert({
                            message: __(
                                "Edit mode enabled. Saving invoice-related changes will automatically replace the linked invoice."
                            ),
                            indicator: "blue",
                        });
                    });
                },
                __("Amend Approved Visa Service"),
                __("Continue")
            );
        },
        __("Actions")
    );
}
