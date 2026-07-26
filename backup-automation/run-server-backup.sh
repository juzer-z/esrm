#!/bin/bash
set -euo pipefail

deployment_dir="/home/frappe/esrm-production/deployment"
backup_dir="/home/frappe/esrm-backups"
compose_file="${deployment_dir}/compose.yaml"
env_file="${deployment_dir}/production.env"

mkdir -p "${backup_dir}"

docker compose \
  --env-file "${env_file}" \
  -f "${compose_file}" \
  exec -T backend \
  bench --site esrm.local backup --with-files --compress

backend_container="$(
  docker compose \
    --env-file "${env_file}" \
    -f "${compose_file}" \
    ps -q backend
)"

if [[ -z "${backend_container}" ]]; then
  echo "Backend container was not found." >&2
  exit 1
fi

docker cp \
  "${backend_container}:/home/frappe/frappe-bench/sites/esrm.local/private/backups/." \
  "${backup_dir}/"

find "${backup_dir}" -maxdepth 1 -type f -mtime +14 -delete

(
  cd "${backup_dir}"
  find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%f\n' \
    | sort \
    | xargs -r sha256sum > SHA256SUMS
)

chown -R frappe:frappe "${backup_dir}"
chmod 750 "${backup_dir}"
find "${backup_dir}" -maxdepth 1 -type f -exec chmod 640 {} +

echo "ESRM backup completed at $(date --iso-8601=seconds)"
