# ERP API

A production-oriented ERP backend built with Django and Django REST Framework, with a React/TypeScript frontend in the same repository.

## What it provides

- Organization, sites, departments and employees
- Role-based and permission-based access control
- Customer and supplier management
- Product catalog and carton pricing
- Purchases and atomic stock intake
- Invoices with historical price snapshots and lifecycle handling
- Inventory balances and immutable stock-movement history
- Payments and deterministic invoice allocation
- Accounting journals, balances, analytics and financial reporting
- Product intelligence for demand, stock cover and reorder recommendations
- Stateful authentication sessions backed by Redis with stateless JWT access tokens
- Authentication throttling and session-aware permissions

## Architecture

```text
React + TypeScript frontend
            |
            v
     Django REST API
            |
   +--------+--------+
   |        |        |
   v        v        v
PostgreSQL Redis    Celery
   |
   +--> transactional source of truth
```

The project keeps domain boundaries explicit: each business area owns its models, serializers, views, URLs, permissions and tests. Transactional business operations use database transactions and row-level locking where required to protect financial and inventory integrity.

The API is served through ASGI, while database transactions remain isolated behind synchronous service boundaries where needed. PostgreSQL is the system of record; Redis supports caching, throttling and authentication-session state. Celery is used for scheduled integrity work and background jobs.

## Authentication and authorization

- JWT access tokens
- Refresh/session state stored in `AuthSession`
- Redis-backed server-side session snapshots
- HttpOnly cookie handling for sensitive authentication flows
- Role and permission checks at the API layer
- Request throttling

## Reporting and product intelligence

The reporting layer reads from authoritative transactional domains and exposes live operational analytics such as sales, purchases, inventory, top products, employee sales, P&L and cash-flow views.

Product intelligence is deterministic and explainable rather than machine-learning based. It derives demand trend, average daily sales, stock cover, estimated margin and reorder recommendations from historical transactional data.

## Frontend

The repository also contains a React/TypeScript ERP workspace built with Vite, Mantine and React Router. It includes responsive workflows for sales, purchasing, inventory, organization and accounting, with permission-aware navigation and validation/error states.

## Infrastructure and quality

- Docker / Docker Compose for PostgreSQL and Redis
- Gunicorn production configuration
- PostgreSQL connection pooling through psycopg 3
- GitHub Actions CI
- Django checks and migration checks
- Application test suites organized by domain
- Frontend TypeScript build verification
- Ruff-based code quality checks

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL and Redis

docker compose up -d

python manage.py migrate
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Tests

```bash
python manage.py test
```

The CI workflow also runs domain-specific test suites against PostgreSQL and builds the React frontend.

## Documentation

Detailed design notes and domain decisions are available under [`docs/`](docs/), including access control, invoice behavior, money conventions, operations/disaster recovery, reporting and intelligence, permissions and testing.
