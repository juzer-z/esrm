ARG ERPNEXT_IMAGE=frappe/erpnext:v15.104.3
FROM ${ERPNEXT_IMAGE}

USER root
COPY --chown=frappe:frappe frappe-apps/esrm_travel /home/frappe/frappe-bench/apps/esrm_travel
RUN sed -i '/location \/assets {/a\        expires 1y;\n        add_header Cache-Control "public, max-age=31536000, immutable";' /templates/nginx/frappe.conf.template

USER frappe
WORKDIR /home/frappe/frappe-bench
RUN ./env/bin/pip install --no-cache-dir --editable ./apps/esrm_travel
RUN mkdir -p sites/assets/esrm_travel/js \
    && cp apps/esrm_travel/esrm_travel/public/js/approval_notification_refresh.js \
        sites/assets/esrm_travel/js/approval_notification_refresh.js
