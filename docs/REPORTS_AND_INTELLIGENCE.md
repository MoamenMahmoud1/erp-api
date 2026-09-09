# Reports, Analytics and Product Intelligence

## Purpose

The ERP reporting layer is read-only and builds on the existing transactional domains. It does not become a second source of truth: invoices, purchases, stock balances, payments and accounting journals remain authoritative.

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

Celery worker
  |
  +--> accounting/tasks.py ------> analytics/report services
  +--> products/tasks.py --------> product intelligence service

Celery Beat
  |
  +--> every 15 minutes: warm common analytics dashboard
  +--> hourly: refresh default product intelligence

Redis
  |
  +--> short-lived report cache
  +--> one-hour product-intelligence cache
```

The same domain services are used by HTTP requests and background jobs. Celery is orchestration only; business calculations remain in domain services.

## Reports and analytics

Existing accounting analytics provide:

- sales KPIs and daily sales trend
- purchase KPIs and daily purchase trend
- inventory totals, valuation and low-stock list
- top products
- sales by employee
- cross-domain dashboard overview with P&L, cash flow and balances

These functions use a short Redis cache controlled by `REPORT_CACHE_TTL`. The scheduled task pre-computes the standard dashboard window without making users pay the query cost on the first request.

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

### Reorder heuristic

The first version intentionally avoids pretending that the ERP has supplier lead-time data when it does not. It uses a target stock coverage window instead:

```text
average_daily_sales = sold_units / lookback_days
target_units = ceil(average_daily_sales * target_stock_days)
reorder_quantity = max(0, target_units - current_stock)
```

This is a planning recommendation only. It does not create a purchase order.

### Slow-moving heuristic

A product is marked slow-moving when it has no sales in the current window, or when its last sale is at least `slow_moving_days` old while stock is still held.

### Cost and margin

Historical invoice `cost_price` is used when captured; otherwise the current product purchase price is used as an explicit fallback. Product intelligence therefore exposes its profitability fields as **estimated** values.

## API

### Product intelligence

```http
GET /api/v1/products/intelligence/
```

Query parameters:

| Parameter | Default | Range | Purpose |
| --- | ---: | ---: | --- |
| `as_of` | today | valid date, not future | Analysis end date |
| `lookback_days` | 30 | 1-365 | Current demand window |
| `forecast_days` | 7 | 1-90 | Demand horizon |
| `target_stock_days` | 14 | 1-180 | Desired stock coverage |
| `slow_moving_days` | 60 | 1-365 | Slow-moving threshold |
| `limit` | 100 | 1-500 | Number of product rows returned |
| `product_id` | none | positive integer | Inspect one product |

The endpoint is read-only and uses the existing authenticated/staff-read permission pattern.

## Celery local development

Install dependencies from `requirements.txt`, make sure Redis is running, then start two processes:

```bash
celery -A core.celery:app worker -l INFO
celery -A core.celery:app beat -l INFO
```

The worker and beat processes use the same Django settings selected by the environment. For local development this is normally `core.settings.settings_dev`.

## Tests

Focused tests follow the existing domain-based test architecture:

```bash
python manage.py test accounting.tests.test_tasks
python manage.py test products.tests.test_intelligence
python manage.py test products.tests.test_tasks
python manage.py test core.tests.test_celery
```

The product-intelligence tests use real Django models and database relationships. Celery task tests call task bodies directly so local validation does not require a live broker.

## Next intelligence steps

The deterministic layer should remain the foundation. Future ML/forecasting work should consume these stable features rather than replace the transactional domain:

1. stronger demand forecasting using seasonality and trend
2. supplier lead-time and safety-stock inputs
3. anomaly detection for unusual sales or stock behavior
4. purchase recommendations with explainable confidence scores
5. customer and product segmentation
