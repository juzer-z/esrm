ARG ERPNEXT_IMAGE=frappe/erpnext:v15.104.3
FROM ${ERPNEXT_IMAGE}

USER root
COPY --chown=frappe:frappe frappe-apps/esrm_travel /home/frappe/frappe-bench/apps/esrm_travel
RUN sed -i '/location \/assets {/a\        expires 1y;\n        add_header Cache-Control "public, max-age=31536000, immutable";' /templates/nginx/frappe.conf.template
RUN sed -i '2i mkdir -p /home/frappe/frappe-bench/sites/assets/esrm_travel/js\ncp /home/frappe/frappe-bench/apps/esrm_travel/esrm_travel/public/js/approval_notification_refresh.js /home/frappe/frappe-bench/sites/assets/esrm_travel/js/approval_notification_refresh.js' /usr/local/bin/nginx-entrypoint.sh

USER frappe
WORKDIR /home/frappe/frappe-bench
RUN ./env/bin/pip install --no-cache-dir --editable ./apps/esrm_travel
