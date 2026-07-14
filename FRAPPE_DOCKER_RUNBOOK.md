# Frappe Docker Runbook

This project can be run locally in Docker using the development stack defined in:

- `docker-compose.frappe-dev.yml`

The compose project name is explicitly set to:

- `esrm_travel_dev`

## What This Stack Provides

- `mariadb`
- `redis-cache`
- `redis-queue`
- `frappe` development container using `frappe/bench:latest`

The repository is mounted into the container at:

- `/workspace`

## Main Working Paths Inside Container

- project root: `/workspace`
- custom app: `/workspace/frappe-apps/esrm_travel`
- bench root once created: `/workspace/frappe-dev/frappe-bench`

## Start Services

```bash
docker compose -f docker-compose.frappe-dev.yml up -d
```

## Open Shell In Dev Container

```bash
docker compose -f docker-compose.frappe-dev.yml exec frappe bash
```

## Bootstrap Bench

```bash
cd /workspace
mkdir -p frappe-dev
cd frappe-dev

bench init --skip-redis-config-generation --frappe-branch version-15 frappe-bench
cd frappe-bench

bench set-config -g db_host mariadb
bench set-config -g redis_cache redis://redis-cache:6379
bench set-config -g redis_queue redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379
bench --site development.localhost set-config developer_mode 1
```

## Create Site

```bash
bench new-site --db-root-password 123 --admin-password admin --mariadb-user-host-login-scope=% development.localhost
```

## Install ERPNext

```bash
bench get-app --branch version-15 erpnext
bench --site development.localhost install-app erpnext
```

## Install ESRM Travel App

```bash
bench get-app /workspace/frappe-apps/esrm_travel
bench --site development.localhost install-app esrm_travel
bench --site development.localhost migrate
```

## Start App Server

```bash
cd /workspace/frappe-dev/frappe-bench
bench start
```

Open:

- `http://localhost:18000/app`

Login:

- user: `Administrator`
- password: `admin`

## Notes

- If `bench init` or `bench get-app` needs internet access, Docker/bench must be allowed to pull dependencies.
- If version compatibility becomes an issue with `version-15`, pin the app and ERPNext/Frappe branches together before installing.
