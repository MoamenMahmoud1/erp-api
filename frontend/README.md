# ERP Frontend

React + TypeScript + Vite frontend for the ERP API.

## Stack

- React 19
- TypeScript
- Vite
- Mantine
- Mantine Charts
- Recharts
- React Router

## Local setup

Use Node.js 22+.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies `/api` to the Django server at `http://127.0.0.1:8000`.

Run the backend separately:

```bash
source ../venv/bin/activate
python ../manage.py runserver
```

## Checks and production build

```bash
npm run typecheck
npm run build
```

The production image is a small Nginx image built from the compiled `dist` directory:

```bash
docker build -t erp-frontend:latest .
docker run --rm -p 8080:80 erp-frontend:latest
```

Use `VITE_API_URL` to point the browser to the API. It is a public browser configuration value, not a secret. For a same-origin deployment, keep it as `/api/v1` and route `/api/` to Django at the reverse-proxy/load-balancer layer.

`VITE_API_PROXY_TARGET` is for local Vite development only.

Never put passwords, private API keys, signing keys, database credentials, Firebase service-account credentials, or other secrets in a `VITE_*` variable. Vite embeds `VITE_*` values in the browser bundle.

The frontend does not ship Django settings, server environment variables, Celery configuration, Redis credentials, database credentials, or service-account files.

## Visual direction

Modern Enterprise + Bento layout + restrained Glassmorphism + Aurora accents + dark/light themes + purposeful motion.

Primary data surfaces stay readable and mostly solid; glass effects are reserved for the shell, cards and overlays.

## Current workspaces

- Dashboard with live sales, purchase, inventory and accounting KPIs
- Sales and purchase lists + confirmation/cancellation actions
- Draft invoice and purchase workflows
- Customer payment collection and supplier payment
- Products, customers, suppliers, coupons and carton pricing
- Inventory locations, movements and stock transfers
- Company, sites and departments
- Accounting overview, accounts, journals, manual journal, ledger, trial balance
- P&L, balance sheet, cash flow
- AR/AP balances and aging
- Expenses, opening balance and accounting periods
