# Access control, sites and employee shifts

## Design rule

The ERP is a modular monolith. Existing domain apps remain responsible for their business rules; access is decided by a combination of role permissions and organizational scope.

```text
Role -> what the user may do
Scope -> where the user may do it
Shift -> whether the user is currently allowed to perform shift-bound operations
```

No separate `stores`, `shop`, or `branch` business apps are required.

## Site hierarchy

`organization.Site` is the location model:

- `head_office`: central administration
- `branch`: a branch
- `store`: a shop; a store may belong to a branch

Employees have a `work_site`. Site-aware transactional records such as invoices, purchases, payments and stock locations retain their site context.

## Role scopes

| Scope | Meaning |
| --- | --- |
| `company` | Access across the company |
| `branch` | A branch and its direct stores |
| `site` | One employee work site |

Permissions are still ordinary Django permissions. Scope does not replace permissions; both checks must succeed.

## Standard roles

The repository provides an idempotent `sync_system_roles` command for the standard role set:

- HQ Admin: company scope
- Finance: company scope
- Branch Manager: branch scope
- Shop Manager: site scope, shift required
- Salesperson: site scope, shift required
- Cashier: site scope, shift required
- Warehouse Operator: site scope, shift required

Run after migrations:

```bash
python manage.py sync_system_roles
```

The command sets the Group permissions to the declared system-role definition instead of accumulating permissions from repeated runs.

## Employee shifts

`accounts.EmployeeShift` is intentionally part of the existing `accounts` app.

A shift represents one employee's working period for one business date. It stores:

- employee
- site
- optional assigned sales vehicle
- opening and closing timestamps
- opening cash
- closing cash and bank/transfer amounts
- closing notes
- open/closed state

An employee can have one shift per business date and at most one open shift.

### Start

`POST /api/v1/accounts/shifts/start/`

The site is taken from the employee work site. A selected vehicle must be an active sales vehicle assigned to the same employee and site.

### Current

`GET /api/v1/accounts/shifts/current/`

Returns the employee's current open shift or `null`.

### Close

`POST /api/v1/accounts/shifts/close/`

The server calculates expected cash and transfer totals from the payment transactions and payment refunds linked to the shift, then stores the actual values and the differences in the audit event.

## Shift-bound operations

For roles with `requires_shift=True`, the backend requires an open shift for operational mutations such as:

- invoice creation/confirmation/cancellation/returns and draft coupon changes
- purchase creation/confirmation/cancellation/returns and supplier payments
- customer collections and payment refunds
- stock transfers

The client never chooses the authoritative site or shift for these operations. The server resolves them from the authenticated employee and current shift.

Company-scope users may explicitly select a site when creating a site-aware draft transaction. They are not forced to have an employee shift.

## Financial accounting

Accounting remains company-level in the current architecture. Shop users do not receive general-ledger or financial-statement permissions. Sales, payments, returns and purchases still generate the existing accounting entries in the backend.

Branch-level accounting reports should only be added once journal entries themselves carry reliable site attribution. Until then, the system must not present company-level accounting as a branch-level result.

## Frontend behavior

The frontend uses `/auth/me/` as the current user context. It exposes:

- effective permissions
- role and role scope
- employee site
- current shift

Navigation and the default landing page are filtered by permissions and role context. This is only a UX optimization; backend permissions and site scoping remain authoritative.

A shop user is directed to `My Shift` first when their role requires a shift and no shift is open. HQ users do not see `My Shift` merely because an administrator role has broad permissions.
