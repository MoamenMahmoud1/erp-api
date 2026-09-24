# Phase 3 — Domain Foundation + Money Conventions

## Scope
Prepare the separated domains for Phase 4 (invoice lifecycle, payment
collection, inventory) WITHOUT implementing those workflows. Establish a
deterministic money foundation, tighten financial invariants, and add focused
tests.

## Postponed (Phase 4+)
- Invoice DRAFT/CONFIRMED/CANCELLED/PAID lifecycle
- ConfirmInvoice / CancelInvoice / ApplyCoupon end-to-end
- PaymentTransaction / PaymentAllocation / ProcessCollection
- StockMovement / inventory ledger
- select_for_update workflows / org isolation / full RBAC

## Files created
- `common/exceptions.py` — small domain-exception base set
- `common/money.py` — Decimal + ROUND_HALF_UP helpers (quantize / serialization
  / non-negativity)
- `common/tests.py` — money helper tests
- `coupons/tests.py` — coupon validity invariant tests
- `docs/MONEY_CONVENTION.md` — money convention documentation

## Files modified
- `invoices/models.py` — quantize money, remove silent clamp on total, add
  DB CheckConstraints (coupon_discount>=0, quantity>=1, unit_price>=0)
- `invoices/api/serializers.py` — make `unit_price` and `coupon_discount`
  read-only (client cannot inject financial values; price snapshot is the
  source of truth)
- `coupons/models.py` — `clean()` + `save() -> full_clean()`, DB
  CheckConstraints (discount_value>=0, percentage<=100, minimum>=0)
- `coupons/api/serializers.py` — translate Django ValidationError to DRF 400
- `products/models.py` — DB CheckConstraints (price>=0, carton_price>=0)
- `payments/models.py` — DB CheckConstraint (amount>=0)

## Principles
- Backend is the financial source of truth. Serializers never let clients set
  authoritative money (coupon_discount, InvoiceItem.unit_price).
- Decimal everywhere; ROUND_HALF_UP; no silent clamping; explicit rejection
  of negative money.
- Django validation for business rules (Coupon.clean), DB constraints for
  invariants that must never be violated (money non-negative, quantity>0).
- Small, focused money helper only — no Money framework/ceremony.