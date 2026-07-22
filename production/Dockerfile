ARG ERPNEXT_IMAGE=frappe/erpnext:v15.104.3
FROM ${ERPNEXT_IMAGE}

USER root
COPY --chown=frappe:frappe frappe-apps/esrm_travel /home/frappe/frappe-bench/apps/esrm_travel

USER frappe
WORKDIR /home/frappe/frappe-bench
RUN ./env/bin/pip install --no-cache-dir --editable ./apps/esrm_travel
