# ERP API

Production-oriented ERP backend and web application built with **Django**, **Django REST Framework**, **PostgreSQL**, **Redis**, and **Celery**.

The repository contains the central business API and a permission-aware **React/TypeScript web frontend**. It is the web/administration side of the ERP platform; the complementary **Flutter mobile client** for sales representatives and warehouse staff lives in [`sales_erp`](https://github.com/MoamenMahmoud1/sales_erp).

## Features

- Organization, sites, departments, employees, roles, and permissions
- Customers, suppliers, products, and carton pricing
- Purchases and atomic stock intake
- Invoices with historical price snapshots and lifecycle transitions
- Inventory balances with an immutable stock-movement ledger
- Payments and deterministic invoice allocation
- Accounting journals, balances, P&L, cash-flow, and operational reporting
- Product intelligence for demand trends, stock cover, margins, and reorder recommendations
- Secure JWT authentication with refresh/session state and throttling
- Redis-backed caching, throttling, and authentication session state
- Celery background and scheduled jobs
- Durable in-app notifications driven by approval workflow events
- Generic direct-vs-approval mutation policy for representative operations

## Architecture

```text
                    React + TypeScript
                          Web App
                             |
                             v
                    Django REST API
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
         PostgreSQL        Redis          Celery
        source of truth   cache/auth     background jobs
                                             |
                                             v
                                      Async notifications
```

The backend keeps domain boundaries explicit and isolates transactional business operations behind service layers. Critical financial and inventory writes use database transactions and row-level locking to preserve integrity under concurrent requests.

The API is served through **WSGI/Gunicorn**. PostgreSQL is the system of record, Redis handles caching/throttling/session workloads, and Celery handles background processing.

## Frontend

The included React/TypeScript frontend provides permission-aware workflows for sales, purchasing, inventory, organization, accounting, reporting, and related administration tasks.

## Quality & Infrastructure

- Docker / Docker Compose
- Separate Docker build targets for Celery worker/beat and Django WSGI web
- Gunicorn production configuration
- psycopg 3 connection pooling
- Redis + Celery worker/beat processes for background jobs
- GitHub Actions CI
- Automated Django, migration, and domain-level tests
- Ruff code-quality checks
- OpenAPI documentation with drf-spectacular

## Development

Start the local infrastructure and background workers without building the Django web image:

```bash
docker compose up -d --build
```

The default Compose stack starts PostgreSQL, Redis, Celery worker, and Celery beat. The Celery services use the `worker` Docker build target and do not execute production `collectstatic` during image build.

For local Django development outside Docker:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

When you are ready to build the Django WSGI image, build the dedicated `web` target:

```bash
docker build --target web -t erp-api:latest .
```

The web image runs `collectstatic` when the container starts, after the production environment has been supplied, so image build does not require production environment variables.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Tests:

```bash
python manage.py test
```

## Related Repository

**Mobile client:** [`MoamenMahmoud1/sales_erp`](https://github.com/MoamenMahmoud1/sales_erp)

Together, `erp-api` and `sales_erp` form the web and mobile applications of the same ERP platform.

## License

This repository is **proprietary**. All rights reserved by the copyright holder. No permission is granted to use, copy, modify, distribute, publish, sublicense, or create derivative works from this code without prior written permission. See [`LICENSE`](LICENSE).
