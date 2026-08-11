frappe.ui.form.on("Ticket Booking", {
    onload(frm) {
        if (frm.is_new() && !frm.doc.booking_owner) {
            frm.set_value("booking_owner", frappe.session.user);
        }
    },

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

    trip_type(frm) {
        update_route_summary(frm);
    },

    refresh(frm) {
        frm.set_df_property("booking_owner", "read_only", frappe.session.user !== "Administrator");
        setup_administrator_amendment(frm);
        set_approved_cost_permissions(frm);
        add_administrator_draft_delete_action(frm);
        add_ticket_cancellation_action(frm);

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

        if (frm.doc.credit_note) {
            frm.add_custom_button(__("Open Credit Note"), () => {
                frappe.set_route("Form", "Sales Invoice", frm.doc.credit_note);
            });
        }
    },
});

frappe.ui.form.on("Ticket Sector", {
    origin(frm) {
        update_route_summary(frm);
    },

    destination(frm) {
        update_route_summary(frm);
    },

    sectors_remove(frm) {
        update_route_summary(frm);
    },
});

function update_route_summary(frm) {
    const airports = [];

    (frm.doc.sectors || []).forEach((sector) => {
        const origin = (sector.origin || "").trim().toUpperCase();
        const destination = (sector.destination || "").trim().toUpperCase();
        if (!origin || !destination) {
            return;
        }

        if (!airports.length) {
            airports.push(origin, destination);
        } else if (airports[airports.length - 1] === origin) {
            airports.push(destination);
        } else {
            airports.push(origin, destination);
        }
    });

    if (frm.doc.trip_type === "Return" && airports.length && airports[airports.length - 1] !== airports[0]) {
        airports.push(airports[0]);
    }

    frm.set_value("route_summary", airports.join("-"));
}

function calculate_profitability(frm) {
    const gross_amount = flt(frm.doc.gross_amount);
    const iata_amount = flt(frm.doc.iata_amount);
    const supplier_cost = flt(frm.doc.supplier_cost);
    const invoice_amount = flt(frm.doc.invoice_amount);

    if (frm.doc.payment_mode === "IATA") {
        frm.set_value("commission", gross_amount - iata_amount);
        frm.set_value("profit", iata_amount > 0 ? invoice_amount - iata_amount : 0);
    } else {
        frm.set_value("commission", 0);
        frm.set_value("profit", supplier_cost > 0 ? invoice_amount - supplier_cost : 0);
    }

    frm.set_value("discount", gross_amount - invoice_amount);
}

function set_approved_cost_permissions(frm) {
    if (frm.is_new() || frm.doc.docstatus !== 1 || frm.doc.approval_status !== "Approved") {
        return;
    }

    if (frappe.session.user === "Administrator") {
        return;
    }

    const is_owner = frappe.session.user === frm.doc.booking_owner;
    const can_enter_cost = is_owner && !frm.doc.cost_entered_by_owner;
    const is_iata = frm.doc.payment_mode === "IATA";
    const iata_missing = flt(frm.doc.iata_amount) <= 0;
    const supplier_cost_missing = flt(frm.doc.supplier_cost) <= 0;

    frm.set_df_property(
        "iata_amount",
        "read_only",
        !(can_enter_cost && is_iata && iata_missing)
    );
    frm.set_df_property(
        "supplier_cost",
        "read_only",
        !(can_enter_cost && !is_iata && supplier_cost_missing)
    );
}

const ADMINISTRATOR_AMENDMENT_FIELDS = [
    "customer",
    "reference",
    "invoice_number",
    "booking_owner",
    "issue_date",
    "passenger_name",
    "passport_no",
    "purpose",
    "pnr",
    "ticket_number",
    "airline",
    "flight_date",
    "flight_number",
    "payment_mode",
    "supplier_reference",
    "travel_type",
    "trip_type",
    "sectors",
    "gross_amount",
    "iata_amount",
    "supplier_cost",
    "invoice_amount",
    "remarks",
    "uploaded_ticket",
];

function setup_administrator_amendment(frm) {
    if (
        frm.is_new()
        || frm.doc.docstatus !== 1
        || frm.doc.approval_status !== "Approved"
    ) {
        return;
    }

    ADMINISTRATOR_AMENDMENT_FIELDS.forEach((fieldname) => {
        frm.set_df_property(fieldname, "read_only", true);
    });
    frm.set_df_property("amendment_reason", "read_only", true);

    if (frappe.session.user !== "Administrator") {
        return;
    }

    frm.add_custom_button(
        __("Amend Approved Booking"),
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
                        ADMINISTRATOR_AMENDMENT_FIELDS.forEach((fieldname) => {
                            frm.set_df_property(fieldname, "read_only", false);
                        });
                        frappe.show_alert({
                            message: frm.doc.sales_invoice
                                ? __(
                                    "Edit mode enabled. Changes will sync to linked draft Sales Invoice {0}; submitted invoices remain protected.",
                                    [frm.doc.sales_invoice]
                                )
                                : __("Edit mode enabled. Save to record this amendment."),
                            indicator: "blue",
                        });
                    });
                },
                __("Amend Approved Booking"),
                __("Continue")
            );
        },
        __("Actions")
    );
}

function add_administrator_draft_delete_action(frm) {
    if (
        frappe.session.user !== "Administrator"
        || frm.is_new()
        || frm.doc.docstatus !== 0
        || frm.doc.approval_status !== "Draft"
    ) {
        return;
    }

    frm.add_custom_button(
        __("Delete Draft Booking"),
        () => frm.savetrash(),
        __("Actions")
    );
}

function add_ticket_cancellation_action(frm) {
    if (
        frappe.session.user !== "Administrator"
        || frm.is_new()
        || frm.doc.docstatus !== 1
        || frm.doc.approval_status !== "Approved"
        || !frm.doc.sales_invoice
        || frm.doc.credit_note
    ) {
        return;
    }

    frm.add_custom_button(
        __("Cancel Ticket / Create Credit Note"),
        () => {
            const original_amount = flt(frm.doc.invoice_amount || frm.doc.gross_amount);
            const dialog = new frappe.ui.Dialog({
                title: __("Cancel Ticket and Create Credit Note"),
                fields: [
                    {
                        fieldname: "original_amount",
                        fieldtype: "Currency",
                        label: __("Original Ticket Amount"),
                        default: original_amount,
                        read_only: 1,
                    },
                    {
                        fieldname: "refund_amount",
                        fieldtype: "Currency",
                        label: __("Refund Before Cancellation Fee"),
                        default: original_amount,
                        reqd: 1,
                    },
                    {
                        fieldname: "cancellation_fee",
                        fieldtype: "Currency",
                        label: __("Cancellation Fee"),
                        default: 0,
                        reqd: 1,
                    },
                    {
                        fieldname: "net_credit_preview",
                        fieldtype: "Currency",
                        label: __("Net Credit Amount"),
                        default: original_amount,
                        read_only: 1,
                    },
                    {
                        fieldname: "cancellation_date",
                        fieldtype: "Date",
                        label: __("Cancellation Date"),
                        default: frappe.datetime.get_today(),
                        reqd: 1,
                    },
                    {
                        fieldname: "cancellation_reason",
                        fieldtype: "Small Text",
                        label: __("Cancellation Reason"),
                        reqd: 1,
                    },
                ],
                primary_action_label: __("Create Draft Credit Note"),
                primary_action(values) {
                    const refund = flt(values.refund_amount);
                    const fee = flt(values.cancellation_fee);
                    if (refund <= 0 || fee < 0 || fee >= refund) {
                        frappe.msgprint(__("Refund must be positive and the fee must be less than the refund."));
                        return;
                    }
                    dialog.hide();
                    frappe.call({
                        method: "esrm_travel.esrm_travel.doctype.ticket_booking.ticket_booking.create_ticket_credit_note",
                        args: {
                            source_name: frm.doc.name,
                            refund_amount: refund,
                            cancellation_fee: fee,
                            cancellation_date: values.cancellation_date,
                            cancellation_reason: values.cancellation_reason,
                        },
                        freeze: true,
                        freeze_message: __("Creating Credit Note..."),
                        callback: (r) => {
                            if (!r.message) {
                                return;
                            }
                            const result = r.message;
                            const document_name = result.name || result;
                            const document_type = result.document_type || __("Credit Note");
                            frappe.show_alert({
                                message: __("{0} {1} created", [document_type, document_name]),
                                indicator: "green",
                            });
                            frm.reload_doc().then(() => {
                                frappe.set_route("Form", "Sales Invoice", document_name);
                            });
                        },
                    });
                },
            });

            const update_preview = () => {
                dialog.set_value(
                    "net_credit_preview",
                    Math.max(
                        flt(dialog.get_value("refund_amount"))
                        - flt(dialog.get_value("cancellation_fee")),
                        0
                    )
                );
            };
            dialog.fields_dict.refund_amount.df.onchange = update_preview;
            dialog.fields_dict.cancellation_fee.df.onchange = update_preview;
            dialog.show();
        },
        __("Actions")
    );
}
