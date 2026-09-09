# Reports, Analytics and Product Intelligence

## Purpose

The reporting layer is read-only and builds on the existing transactional domains. It does not become a second source of truth: invoices, purchases, stock balances, payments and accounting journals remain authoritative.

## Organization and branch model

`organization.Company` is the single company context. A company can have multiple `Site` records:

- `head_office`
- `branch`
- `store`

A store may belong to a branch. Employees can be assigned to a work site, and branch-scoped users see and operate on their branch plus its child stores. Head-office users can operate across the company's sites.

Invoices and purchases carry a `site` so sales and receiving are attributable to the branch/store. Stock locations also carry a `site`; each site can have one active main warehouse, plus sales-vehicle locations. Stock transfers may move inventory between accessible locations.

## Architecture

```text
HTTP/API
  |
  +--> accounting/api/*
  |       |
  |       +--> accounting/services/analytics.py
  |       +--> accounting/services/statements.py
  |       +--> accounting/services/balances.py
  |
  +--> products/api/intelligence.py
          |
          +--> products/services/intelligence.py

Dashboard
  |
  +--> live report calculations for changing operational data
  +--> Company master-data counters for cheap global counts

Company counters
  |
  +--> Product / Invoice / Customer / Supplier writes update counters in O(1)
  +--> daily Celery reconciliation repairs any drift

Celery
  |
  +--> currently used only for the daily counter-integrity check
  +--> reserved for heavy historical analytics and intelligence jobs later
```

The operational dashboard is intentionally live. It does not wait for a cache refresh and does not depend on Celery for freshness.

## Master-data counters

The `organization.Company` singleton stores these operational counters:

- `product_count`
- `invoice_count`
- `customer_count`
- `supplier_count`

Domain app signals update the relevant counter when a record is created or deleted. Updates use database-side `F()` expressions so concurrent writes do not require a read-modify-write race-prone sequence.

These counters are used only for cheap global counts. They do not replace date-filtered analytics such as sales for a selected period, P&L, cash flow, inventory valuation, or top products; those reports remain live and query their authoritative transactional data.

## Counter integrity

A daily Celery Beat job runs at **02:00 UTC** and recomputes the counters from the authoritative tables. It then writes the corrected values and records `counters_reconciled_at`.

This gives the system two protections:

1. normal writes maintain counters immediately and cheaply;
2. the daily reconciliation catches drift caused by bulk ORM operations, data repair scripts, imports, or other code paths that bypass model signals.

## Reports and analytics

Existing accounting analytics provide:

- sales KPIs and daily sales trend
- purchase KPIs and daily purchase trend
- inventory totals, valuation and low-stock list
- top products
- sales by employee
- cross-domain dashboard overview with P&L, cash flow and balances

Operational analytics accept a `site` filter so branch/store sales, purchases, stock, top products and employee sales can be isolated. The broader financial statements still use the company-level journal context.

## Product intelligence v1

`products/services/intelligence.py` is an explainable heuristic layer, not machine learning.

For active products it calculates:

- current-period sold units
- previous-period sold units
- average daily sales
- demand trend percentage
- forecast units for the next configurable number of days
- current stock and inventory value
- days of stock cover
- estimated COGS, gross profit and gross margin
- last sale and days since last sale
- velocity band (`fast`, `steady`, `slow`, `no_sales`)
- stock status (`out_of_stock`, `reorder`, `no_demand`, `healthy`)
- recommended reorder quantity
- plain-language recommendation

The v1 calculation is live and deterministic. It does not use a dashboard cache and it does not create purchase orders automatically.

### Reorder heuristic

The first version intentionally avoids pretending that the ERP has supplier lead-time data when it does not. It uses a target stock coverage window instead:

```text
average_daily_sales = sold_units / lookback_days
target_units = ceil(average_daily_sales * target_stock_days)
reorder_quantity = max(0, target_units - current_stock)
```

This is a planning recommendation only.

### Slow-moving heuristic

A product is marked slow-moving when it has no sales in the current window, or when its last sale is at least `slow_moving_days` old while stock is still held.

### Cost and margin

Historical invoice `cost_price` is used when captured; otherwise the current product purchase price is used as an explicit fallback. Product intelligence therefore exposes profitability fields as **estimated** values.

## API

### Product intelligence

```http
GET /api/v1/products/intelligence/
```

### Operational branch filtering

Analytics endpoints accept `site=<site_id>` to isolate one branch/store:

```http
GET /api/v1/accounting/analytics/sales/?site=12
GET /api/v1/accounting/analytics/purchases/?site=12
GET /api/v1/accounting/analytics/inventory/?site=12
GET /api/v1/accounting/analytics/top-products/?site=12
GET /api/v1/accounting/analytics/sales-by-employee/?site=12
GET /api/v1/accounting/analytics/overview/?site=12
```

The same site is selectable by name in the sales and purchasing frontend forms instead of exposing raw IDs to users.

## Celery local development

Install dependencies from `requirements.txt`, make sure Redis is running, then start the worker and Beat scheduler when you want to exercise the scheduled integrity check:

```bash
celery -A core.celery:app worker -l INFO
celery -A core.celery:app beat -l INFO
```

The current Beat schedule contains only the daily counter reconciliation. Heavy historical analytics jobs are intentionally deferred until their query/model design is finalized.

## Tests

Focused tests include:

```bash
python manage.py test organization.tests.test_metrics
python manage.py test core.tests.test_celery
python manage.py test products.tests.test_intelligence
```

The counter tests verify transactional create/delete updates and daily-style drift repair. Product-intelligence tests continue to use real Django models and database relationships. Branch-aware invoice, purchase, employee, and inventory behavior should be covered by the existing domain/API test suites before deployment.
