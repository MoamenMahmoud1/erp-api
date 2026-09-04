# Backend Money Convention

## Principle

The backend is the **source of truth** for all financial values. The client
(Flutter) is never trusted for authoritative totals, discounts, or prices.

Examples already enforced:

- `InvoiceItem.unit_price` is a **read-only** serializer field — the backend
  snapshots `Product.price` at invoice creation. The client can never supply
  it.
- `Invoice.coupon_discount` is a **read-only** serializer field — it is
  authoritative and computed by the backend (starting Phase 4); it can never
  be injected by the client.

## Representation

- All monetary values are stored as **`Decimal`** (`max_digits=12,
  decimal_places=2`).
- **Never use `float` for financial calculations or money input.**
  Python `float` cannot represent many decimal values exactly, which breaks
  determinism. The `common.money` helper rejects `float` (`InvalidMoney`).

## Rounding

- Deterministic rounding: **`ROUND_HALF_UP`** for all currency arithmetic.
- All money is quantified to **2 decimal places** via
  `common.money.quantize_money()`.
- There is **no silent clamping**. Negative results or invalid totals raise
  an explicit error (or are prevented by DB constraints) rather than being
  quietly forced to zero.

## Non-negativity

- Negative monetary values are **explicitly rejected** where the business rule
  requires non-negative values:
  - Via Django handlers/`MinValueValidator` for input validation.
  - Via database `CheckConstraint`s for invariants that must never be violated
    (see below).

## Minor units (interop)

- The Flutter `Money` type works in integer minor units.
- `common.money.to_minor_units()` / `from_minor_units()` convert between
  `Decimal` and integer minor units for API coordination.
- The backend persists `Decimal`; minor units are only a serialization/
  interop concern, not a storage format.

## Where the helpers live

`erp-api/common/money.py` (small, function-based):

- `money_decimal(value)` — coerce to `Decimal`, reject `float`.
- `quantize_money(value)` — round to 2dp with ROUND_HALF_UP.
- `ensure_non_negative(value)` -> quantized, non-negative `Decimal`.
- `to_minor_units(value)` / `from_minor_units(int)` — interop.

`erp-api/common/exceptions.py` defines `DomainError`, `InvalidMoney`,
`InvalidBusinessOperation`, `InvalidDiscount` for domain/business errors.

## Database invariants (enforced at the DB)

- `coupon_discount >= 0` (Invoice)
- `unit_price >= 0` (InvoiceItem)
- `quantity >= 1` (InvoiceItem)
- `product.price >= 0`
- `carton_price >= 0` (CartonPricing)
- `coupon.discount_value >= 0`
- coupon percentage `<= 100`
- `coupon.minimum_invoice_amount >= 0`
- `payment.amount >= 0`

These are the financial invariants that must never be violated. Business rules
(beyond raw invariants) live in Django validation / domain logic, not as DB
constraints.