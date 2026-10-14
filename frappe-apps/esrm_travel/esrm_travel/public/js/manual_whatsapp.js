(function () {
    function normalise_phone(value) {
        let digits = String(value || "").replace(/\D/g, "");
        if (digits.startsWith("00")) digits = digits.slice(2);
        if (digits.startsWith("01") && digits.length === 11) digits = `88${digits}`;
        return digits;
    }

    function whatsapp_url(phone, message) {
        return `https://wa.me/${normalise_phone(phone)}?text=${encodeURIComponent(message || "")}`;
    }

    function open_payload(payload) {
        const launch = (phone) => {
            const digits = normalise_phone(phone);
            if (digits.length < 8) {
                frappe.msgprint(__("Enter a valid WhatsApp number with country code."));
                return;
            }
            const note = payload.operator_note
                ? `<br><br><b>${__("Before sending")}:</b> ${frappe.utils.escape_html(payload.operator_note)}`
                : "";
            frappe.confirm(
                __("Open the prepared WhatsApp message for {0} ({1})?", [
                    frappe.utils.escape_html(payload.recipient || __("recipient")),
                    digits,
                ]) + note,
                () => window.open(whatsapp_url(digits, payload.message), "_blank", "noopener")
            );
        };

        if (payload.phone) {
            launch(payload.phone);
            return;
        }
        frappe.prompt(
            [{
                fieldname: "phone",
                fieldtype: "Data",
                label: __("WhatsApp Number for {0}", [payload.recipient || __("recipient")]),
                description: __("Use the international format, for example 8801XXXXXXXXX."),
                reqd: 1,
            }],
            (values) => launch(values.phone),
            __("WhatsApp number not configured"),
            __("Continue")
        );
    }

    window.esrm_offer_manual_whatsapp = function (frm, event) {
        if (!frm || frm.is_new()) return;
        frappe.call({
            method: "esrm_travel.manual_whatsapp.get_manual_whatsapp_payload",
            args: { doctype: frm.doc.doctype, name: frm.doc.name, event: event || "workflow" },
            callback: (response) => {
                if (response.message) open_payload(response.message);
            },
        });
    };

    window.esrm_offer_manual_whatsapp_batch = function (doctype, names, event) {
        if (!names || !names.length) return;
        frappe.call({
            method: "esrm_travel.manual_whatsapp.get_manual_whatsapp_payloads",
            args: { doctype, names, event: event || "workflow" },
            callback: (response) => {
                const payloads = response.message || [];
                if (!payloads.length) return;
                if (payloads.length === 1) {
                    open_payload(payloads[0]);
                    return;
                }
                const rows = payloads.map((payload) => {
                    const recipient = frappe.utils.escape_html(payload.recipient || __("Recipient"));
                    if (!payload.phone) {
                        return `<div class="mb-3"><b>${recipient}</b><br><span class="text-muted">${__("WhatsApp number is not configured.")}</span></div>`;
                    }
                    const url = whatsapp_url(payload.phone, payload.message);
                    return `<div class="mb-3"><b>${recipient}</b> (${payload.phone})<br><a class="btn btn-xs btn-default mt-1" target="_blank" rel="noopener" href="${frappe.utils.escape_html(url)}">${__("Open WhatsApp")}</a></div>`;
                }).join("");
                frappe.msgprint({
                    title: __("Manually send WhatsApp notifications"),
                    message: rows,
                    wide: true,
                    indicator: "green",
                });
            },
        });
    };
})();
