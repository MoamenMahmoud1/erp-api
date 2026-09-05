# Invoice Domain & Lifecycle

## Status: IMPLEMENTED (including inventory integration and PAID transition)

## Scope

The `invoices` app is the authoritative owner of invoice financial state. It
defines the invoice lifecycle, owns all money calculations (via
`InvoiceCalculator`), and exposes business operations (`ConfirmInvoice`,
`CancelInvoice`, `ApplyCoupon`) instead of letting clients mutate state
directly.

## Lifecycle

```
DRAFT
  ├── CONFIRMED   (ConfirmInvoice — also decreases stock via SALE movement)
  └── CANCELLED   (CancelInvoice)

CONFIRMED
  ├── CANCELLED   (CancelInvoice)
  └── PAID        (ProcessCollection — payment domain transitions when cumulative
                   allocations reach invoice.total)
```

- New invoices start `DRAFT`.
- Transitions happen ONLY through the explicit business operations. There is
  no arbitrary `PATCH status`.
- `CANCELLED` and `PAID` are terminal.
- `PAID` is owned by the payment domain: `ProcessCollection` transitions
  `CONFIRMED -> PAID` when cumulative allocations reach `invoice.total`.

## Inventory integration (ConfirmInvoice)

When a DRAFT invoice is confirmed:

1. Lock the invoice (`select_for_update`).
2. Verify it is still DRAFT.
3. Resolve the source location — the active `SALES_VEHICLE` location bound to
   `invoice.created_by`.
4. Decrease `StockBalance` for each line item from that location.
5. Create a `SALE` `StockMovement` with `StockMovementItem` rows.
6. Transition the invoice to `CONFIRMED`.

All steps run inside one `transaction.atomic()`. Any failure rolls back
stock, movement, and status together.

The source location is NOT configurable by the client. It is derived from the
employee/sales-vehicle relationship already modeled in `StockLocation`.

## Authoritative calculation (`invoices/calculator.py`)

There is ONE calculation path (`InvoiceCalculator`). Serializers, views and
model properties all delegate to it — they do not duplicate formulas.

```
items ──> unit_price × quantity ──> subtotal
subtotal ──> (coupon rules) ──> discount ──> total
```

- `subtotal` = Σ(unit_price × quantity), quantized to 2dp (ROUND_HALF_UP).
- `discount` = the persisted `coupon_discount` snapshot.
- `total`   = subtotal − discount (no silent clamping; a negative is a bug).
- percentage discounts: subtotal × value / 100 (value ≤ 100 ⇒ never negative).
- fixed discounts: may not exceed subtotal → raises `InvalidDiscount`.

## Financial immutability

- `InvoiceItem.unit_price` is a historical snapshot taken from
  `Product.price` at creation. Later product price changes never affect it.
- `coupon_discount` is a persisted snapshot written when a coupon is applied.
  Editing or deactivating the coupon afterwards does not change the invoice.
- `status`, `coupon_discount`, `unit_price`, `subtotal`, `total` are all
  read-only in the API; the `InvoiceViewSet` does not expose generic
  update/delete.

## coupon_discount decision (why A, not B)

`coupon_discount` is a persisted **authoritative snapshot** (option A), not a
live derivation from the coupon (option B). Rationale: a coupon is
reference data and may be edited or deactivated after an invoice is finalized.
If totals were derived from the coupon, historical invoices would silently
change. By persisting the discount at the moment it is applied, confirmed
invoices are stable. The client never sets this value.

## Coupon application (`ApplyCoupon`)

Only `DRAFT` invoices can receive/change a coupon. `ApplyCoupon` validates:

- coupon exists, is active
- current time within `valid_from` / `valid_until`
- subtotal ≥ `minimum_invoice_amount`
- discount rules produce a valid non-negative total

The API accepts only a coupon `code`; the backend computes and persists the
discount.

## Concurrency

State transitions run inside `transaction.atomic()` and lock the invoice row
with `select_for_update()`, then re-check the current state. The state guard
(together with row locking on PostgreSQL, DB-level serialization on SQLite)
prevents two operators from confirming/cancelling the same invoice
simultaneously.

## Paid / outstanding (derived, never client-written)

```python
paid_amount = Sum("payment_allocations__cash_amount")
               + Sum("payment_allocations__transfer_amount")
outstanding_amount = total - paid_amount
```

These are derived from authoritative `PaymentAllocation` rows. The client
cannot write them. There is no independently editable balance column.

## Money

Decimal + ROUND_HALF_UP + no silent clamping (see `docs/MONEY_CONVENTION.md`
and `common/money.py`). No floats anywhere in financial math.