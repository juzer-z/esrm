frappe.ui.form.on("General Service Order", {
    refresh(frm) {
        frm.set_query("service_offering", () => ({ filters: { active: 1 } }));
        frm.set_df_property("service_owner", "read_only", frappe.session.user !== "Administrator");
        if (frm.is_new() && !frm.doc.service_owner) frm.set_value("service_owner", frappe.session.user);
        setup_amendment(frm);
        setup_copy_to_draft(frm);
        if (frm.doc.sales_invoice) {
            frm.add_custom_button(__("Open Sales Invoice"), () => frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice), __("Actions"));
        }
    },
    service_offering(frm) {
        if (!frm.doc.service_offering) return;
        frappe.call({
            method: "esrm_travel.esrm_travel.doctype.general_service_order.general_service_order.get_offering_defaults",
            args: { offering_name: frm.doc.service_offering },
            callback: (r) => {
                if (!r.message) return;
                ["service_family", "calculation_profile", "description", "print_profile"].forEach((f) => frm.set_value(f, r.message[f]));
                frm.clear_table("charges");
                (r.message.charges || []).forEach((values) => Object.assign(frm.add_child("charges"), values));
                frm.refresh_field("charges");
                calculate(frm);
            },
        });
    },
    charges_add: calculate,
    charges_remove: calculate,
});

function setup_copy_to_draft(frm) {
    if (frm.is_new()) return;

    frm.add_custom_button(__("Copy to New Draft"), () => {
        const copy = frappe.model.copy_doc(frm.doc);
        Object.assign(copy, {
            approval_status: "Draft",
            status: "Draft",
            invoice_status: "Not Invoiced",
            sales_invoice: null,
            invoice_number: null,
            entry_date: frappe.datetime.get_today(),
            amendment_reason: null,
            last_amended_by: null,
            last_amended_at: null,
            amendment_count: 0,
        });
        if (frappe.session.user !== "Administrator") {
            copy.service_owner = frappe.session.user;
        }
        frappe.set_route("Form", copy.doctype, copy.name);
    }, __("Actions"));
}

frappe.ui.form.on("General Service Charge", {
    quantity: calculate, rate: calculate, percentage: calculate, basis_amount: calculate,
    included_in_invoice: calculate, is_revenue: calculate, is_withholding: calculate, actual_cost: calculate,
});

function calculate(frm) {
    let invoice = 0, withholding = 0, revenue = 0, cost = 0, ait_withholding = 0;
    (frm.doc.charges || []).forEach((row) => {
        const amount = flt(row.percentage) ? flt(row.basis_amount) * flt(row.percentage) / 100 : flt(row.quantity || 1) * flt(row.rate);
        frappe.model.set_value(row.doctype, row.name, "amount", amount);
        if (row.included_in_invoice) invoice += amount;
        if (row.is_withholding) {
            withholding += Math.abs(amount);
            if (row.charge_type === "AIT") ait_withholding += Math.abs(amount);
        }
        if (row.is_revenue) revenue += amount;
        cost += flt(row.actual_cost);
    });
    frm.set_value("invoice_amount", invoice);
    frm.set_value("expected_withholding", withholding);
    frm.set_value("net_expected_receipt", invoice - withholding);
    frm.set_value("revenue_amount", revenue);
    frm.set_value("total_cost", cost);
    frm.set_value("profit", revenue - cost - ait_withholding);
}

const AMEND_FIELDS = ["customer","reference","invoice_number","entry_date","service_family","service_offering","calculation_profile","subject","description","client_reference","purchase_order","attention_to","service_period_from","service_period_to","currency","print_profile","signatory_name","signatory_designation","charges","applicants","annexure_details","customer_remarks"];
function setup_amendment(frm) {
    if (frm.is_new() || frm.doc.docstatus !== 1 || frm.doc.approval_status !== "Approved") return;
    AMEND_FIELDS.forEach((f) => frm.set_df_property(f, "read_only", true));
    if (frappe.session.user !== "Administrator") return;
    frm.add_custom_button(__("Amend Approved Service"), () => {
        frappe.prompt([{fieldname:"reason",fieldtype:"Small Text",label:__("Amendment Reason"),reqd:1}], (v) => {
            frm.set_value("amendment_reason", v.reason).then(() => AMEND_FIELDS.forEach((f) => frm.set_df_property(f, "read_only", false)));
        }, __("Amend Approved Service"), __("Continue"));
    }, __("Actions"));
}
