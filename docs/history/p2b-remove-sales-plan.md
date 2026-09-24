# Phase 2B — `sales` removed, true domain separation (COMPLETED)

## Outcome

The `sales` app is **completely removed** (it held no independent business
concept). Each transactional domain now owns its full stack — models,
business rules, serializers, views, URLs, permissions, tests, migrations.

## What was removed
- Entire `sales/` package (models, api/, urls, permissions, admin, tests,
  apps, migrations).
- `sales.apps.SalesConfig` from `INSTALLED_APPS`.
- `path("api/v1/sales/", ...)` from `core/urls.py`.
- `sales/migrations/0001_initial.py` + legacy `sales_*` tables (all empty).

## What each domain now owns

| App | Models | API path | Migration |
|-----|--------|----------|-----------|
| customers | Customer | `/api/v1/customers/` | 0001_initial |
| products  | Product, CartonPricing | `/api/v1/products/`, `/api/v1/carton-pricings/` | 0001_initial |
| coupons   | Coupon (discount) | `/api/v1/coupons/` | 0001_initial |
| invoices  | Invoice, InvoiceItem | `/api/v1/invoices/` | 0001_initial |
| payments  | Payment | `/api/v1/payments/` | 0001_initial |
| inventory | (reserved, empty) | — | — |

## Key domain decisions

- Old `sales.Coupon` (name, units_per_carton, carton_price) was **carton/pack
  pricing**, not a discount. Renamed to `products.CartonPricing`.
- New `coupons.Coupon` models the discount concept: `code`, `discount_type`
  (fixed/percentage), `discount_value`, `minimum_invoice_amount`, `is_active`,
  `valid_from`, `valid_until` + a backend `clean()` guard (percentage <= 100).
- `Invoice.coupon` now targets `coupons.Coupon`.
- `InvoiceItem.unit_price` snapshots product price at invoice creation so
  later `Product.price` changes never alter historical invoice financials.
- Money stays `Decimal` (no minor-unit migration this phase).

## API routing

All domain routers use `SimpleRouter` (no api-root view) and are included at
shared `api/v1/` prefix so each resource sits at its domain path.

## Migration strategy

Because all six business tables were empty (verified) and `db.sqlite3` is a
gitignored dev artifact, legacy tables + stale migration records were dropped
and each domain rebuilt from a fresh canonical `0001_initial`. Real
`accounts`/`organization` data was preserved (verified 1 user intact).

## Verification (all passing)
- `manage.py check` — no issues
- `manage.py makemigrations --check --dry-run` — no changes
- `manage.py migrate` — fresh canonical tables
- `manage.py test` — 133 tests OK
- Route resolution for all domains + carton-pricings
- No `sales` in INSTALLED_APPS; no `/api/v1/sales/` code refs remain
- Flutter API repos updated: `/sales/customers` -> `/customers`,
  `/sales/products` -> `/products`

## Remaining technical debt (later phases)
- Invoice lifecycle (DRAFT/CONFIRMED/CANCELLED/PAID)
- PaymentTransaction / PaymentAllocation / ProcessCollection
- inventory StockMovement ledger
- Organization/site isolation + full RBAC
- Flutter `lib/features/sales/` is a Dart feature folder (app UI), not a
  backend API path; renaming is a separate Flutter-frontend decision.
