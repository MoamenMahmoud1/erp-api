# ERP API

Production-oriented ERP platform with a Django/DRF backend and a React/TypeScript web client. The complementary Flutter mobile client lives in [`sales_erp`](https://github.com/MoamenMahmoud1/sales_erp).

## Repository structure

```text
erp-api/
├── backend/       Django, DRF, domain apps, Celery, Gunicorn, backend Dockerfile
├── frontend/      React + TypeScript + Vite + Nginx
├── infra/         Docker Compose and operational/local scripts
├── docs/          Current architecture/development/operations + historical notes
├── .github/       CI workflows
├── .env.example   Shared local/CI environment template
├── README.md
└── LICENSE
```

The repository is intentionally split at the service boundary: backend code does not depend on the frontend source tree, the frontend does not contain Django code, and project-level container orchestration lives under `infra/`.

## Backend

Built with **Django 6**, **Django REST Framework**, **PostgreSQL**, **Redis**, **Celery**, and **Gunicorn**.

The backend is a modular monolith. Domain apps own their models, querysets, API layer, permissions, services and tests. Transactional financial and inventory operations use database transactions and row-level locking.

Core capabilities include organization and role-based access control, customer assignment and employee shifts, invoices and returns, purchases, inventory movements and stock transfers, payments/refunds, accounting journals and reports, product intelligence, notifications, and idempotent critical writes.

The backend is synchronous WSGI-first. Celery is reserved for background and scheduled work that does not belong on the request path.

## Frontend

The `frontend/` directory contains the permission-aware React/TypeScript administration web application.

See [`frontend/README.md`](frontend/README.md) for setup, build and deployment details.

## Infrastructure

`infra/compose.yaml` defines the local PostgreSQL, Redis, Celery worker and Celery Beat services.

The backend image is built from `backend/Dockerfile` and has separate `web` and `worker` targets. The frontend image is built independently from `frontend/Dockerfile` and served by Nginx.

Run the local infrastructure from the repository root:

```bash
docker compose --env-file .env -f infra/compose.yaml up -d --build
```

Copy `.env.example` to `.env` before starting services.

## Local backend development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py runserver
```

Project migration files are intentionally not committed. Development and test settings therefore use Django's migrationless/syncdb path to build the current schema from model state.

## Tests

From the repository root:

```bash
python backend/manage.py test
```

GitHub Actions splits the test suite by domain so failures point to the relevant business area.

## Documentation

Current guidance lives under:

- `docs/architecture/`
- `docs/development/`
- `docs/operations/`

Historical phase and implementation notes are kept under `docs/history/` and are not the current source of truth.

## Quality and security

The repository uses GitHub Actions, Django system/deploy checks, domain-focused tests, Docker multi-stage builds, PostgreSQL and Redis-backed services, Gunicorn WSGI deployment, and OpenAPI generation with drf-spectacular.

Ruff remains available as an optional local development tool; it is not part of the GitHub CI pipeline.

## Related repository

**Mobile client:** [`MoamenMahmoud1/sales_erp`](https://github.com/MoamenMahmoud1/sales_erp)

Together, the two repositories form the web and mobile clients of the same ERP platform.

## License

This repository is **proprietary**. All rights reserved by the copyright holder. No permission is granted to use, copy, modify, distribute, publish, sublicense, or create derivative works from this code. See [`LICENSE`](LICENSE).
