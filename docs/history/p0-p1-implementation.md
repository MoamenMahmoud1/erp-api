# P0/P1 Business Logic Implementation

The ERP API is sync-first. Native async is intentionally reserved for isolated operations that materially benefit from asynchronous I/O.

## P0
- Invoice cancellation is blocked while the invoice has unreversed money; confirmed cancellation reverses the original SALE movement atomically.
- Payment refunds are immutable `PaymentRefund` records and never rewrite the original collection transaction.
- Inventory exposes locations, current stock, movements and stock transfers through a dedicated API.
- Sales returns are paid-invoice workflows: they validate remaining quantities, create a refund, restore saleable stock and create a `SALEABLE_RETURN` movement.
- Invoice drafts can be edited/deleted; confirmation remains the state boundary.
- Coupon references are immutable from the invoice API; application/removal are explicit draft operations.

## P1
- Confirmed purchase returns decrease warehouse stock through `PURCHASE_RETURN` movements.
- Products can be archived with `is_active`; new purchases/invoices/transfers only accept active products.
- Carton pricing is associated with a product.
- Transactional domains use queryset managers for visibility and reusable backend filtering.
- Domain services are split by use case; cross-domain helpers live in the root `services/` package.
- Tests are split by domain/use case instead of large monolithic modules.
