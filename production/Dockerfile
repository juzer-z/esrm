ARG ERPNEXT_IMAGE=frappe/erpnext:v15.104.3
FROM ${ERPNEXT_IMAGE}

USER root
COPY --chown=frappe:frappe frappe-apps/esrm_travel /home/frappe/frappe-bench/apps/esrm_travel
COPY --chown=frappe:frappe frappe-apps/hrms /home/frappe/frappe-bench/apps/hrms
RUN sed -i '/location \/assets {/a\        expires 1y;\n        add_header Cache-Control "public, max-age=31536000, immutable";' /templates/nginx/frappe.conf.template
RUN sed -i '2i mkdir -p /home/frappe/frappe-bench/sites/assets/esrm_travel/js /home/frappe/frappe-bench/sites/assets/hrms\ncp /home/frappe/frappe-bench/apps/esrm_travel/esrm_travel/public/js/approval_notification_refresh.js /home/frappe/frappe-bench/sites/assets/esrm_travel/js/approval_notification_refresh.js\ncp -a /home/frappe/frappe-bench/apps/hrms/hrms/public/. /home/frappe/frappe-bench/sites/assets/hrms/' /usr/local/bin/nginx-entrypoint.sh

USER frappe
WORKDIR /home/frappe/frappe-bench
RUN ./env/bin/pip install --no-cache-dir --editable ./apps/esrm_travel --editable ./apps/hrms
RUN printf '\nhrms\n' >> ./sites/apps.txt
RUN bench set-config -g socketio_port 9000
RUN cd ./apps/hrms && yarn install --frozen-lockfile
RUN bench build --app hrms
