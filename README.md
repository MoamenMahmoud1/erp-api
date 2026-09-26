# ERP API

ERP platform with a Django/DRF backend and a React/TypeScript web client. The complementary Flutter mobile client lives in [\`sales_erp\`](https://github.com/MoamenMahmoud1/sales_erp).

## Repository structure

\`\`\`text
erp-api/
├── backend/       Django, DRF, domain apps, Celery, Gunicorn, backend Dockerfile
├── frontend/      React + TypeScript + Vite + Nginx
├── infra/         Gateway and operational scripts
├── docs/          Current architecture/development/operations + historical notes
├── .github/       CI workflows
├── .env.example   Example environment template
├── compose.yaml   Single full-stack Docker Compose definition
├── README.md
└── LICENSE
\`\`\`

The repository uses a single Compose entry point at the repository root. Gateway configuration lives under \`infra/gateway/\`.

## Backend

Built with **Django 6**, **Django REST Framework**, **PostgreSQL**, **Redis**, **Celery**, and **Gunicorn**.

The backend is a modular monolith. Domain apps own their models, querysets, API layer, permissions, services and tests. Financial and inventory operations use database transactions and row-level locking.

Core capabilities include organization and role-based access control, customer assignment and employee shifts, invoices and returns, purchases, inventory movements and stock transfers, payments/refunds, accounting journals and reports, product intelligence, notifications, and idempotent critical writes.

The backend is synchronous WSGI-first. Celery is reserved for background and scheduled work that does not belong on the request path.

## Full-stack Docker Compose

The root \`compose.yaml\` runs the complete web stack:

- PostgreSQL
- Redis
- one-time Django migrations
- Django/Gunicorn API
- Celery worker
- Celery Beat
- React/Vite production build served by Nginx
- Nginx gateway

The default Compose runtime uses \`core.settings.settings_dev\` so the HTTP-only local gateway works correctly at \`http://localhost:8080\`. Production settings should only be enabled behind a TLS-terminating edge/proxy with explicit production environment values.

### Start everything

From the repository root:

\`\`\`bash
cp .env.example .env
docker compose config
docker compose up -d --build
docker compose ps
\`\`\`

Open the application at:

\`\`\`text
http://localhost:8080
\`\`\`

Useful endpoints include:

\`\`\`text
http://localhost:8080/health/live/
http://localhost:8080/health/ready/
http://localhost:8080/admin/
\`\`\`

When API docs are enabled in the environment:

\`\`\`text
http://localhost:8080/api/v1/docs/swagger/
http://localhost:8080/api/v1/docs/redoc/
\`\`\`

View service logs with:

\`\`\`bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
docker compose logs -f gateway
\`\`\`

Stop the stack with:

\`\`\`bash
docker compose down
\`\`\`

The PostgreSQL data volume is named \`erp-api_postgres_data\` and is intentionally preserved by a normal \`docker compose down\`.

### Compose environment selection

By default, Compose loads \`.env\`. The \`ENV_FILE\` variable can point to another environment file:

\`\`\`bash
ENV_FILE=.env.prod docker compose --env-file .env.prod up -d --build
\`\`\`

This is useful for CI validation without committing real secrets.

## Local backend development without the full stack

\`\`\`bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py runserver
\`\`\`

Development and test settings use the same migration history as production.

## Tests

From the repository root:

\`\`\`bash
python backend/manage.py test
\`\`\`

GitHub Actions splits the test suite by domain so failures point to the relevant business area.

## Documentation

Current guidance lives under:

- \`docs/architecture/\`
- \`docs/development/\`
- \`docs/operations/\`

Historical phase and implementation notes are kept under \`docs/history/\` and are not the current source of truth.

## Quality and security

The repository uses GitHub Actions, Django checks, domain-focused tests, Docker builds, PostgreSQL, Redis, Gunicorn, and OpenAPI generation with drf-spectacular.

Ruff remains available as an optional local development tool; it is not part of the GitHub CI pipeline.

## Related repository

**Mobile client:** [\`MoamenMahmoud1/sales_erp\`](https://github.com/MoamenMahmoud1/sales_erp)

Together, the two repositories form the web and mobile clients of the same ERP platform.

## License

This repository is **proprietary**. All rights reserved by the copyright holder. No permission is granted to use, copy, modify, distribute, publish, sublicense, or create derivative works from this code. See [\`LICENSE\`](LICENSE).
