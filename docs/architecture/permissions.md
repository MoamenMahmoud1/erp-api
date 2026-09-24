# Permissions

The API is the security boundary. The React frontend uses the same effective permissions only to hide modules and guard routes; frontend checks never replace backend authorization.

## Model permissions

All standard CRUD resources use explicit Django model permissions:

- `view_<model>` for read access
- `add_<model>` for create
- `change_<model>` for update
- `delete_<model>` for delete

`is_staff` is not treated as a substitute for these permissions.

## Business-action permissions

| Domain | Permission | Purpose |
| --- | --- | --- |
| Invoices | `invoices.confirm_invoice` | Confirm a draft invoice |
| Invoices | `invoices.cancel_invoice` | Cancel a confirmed invoice |
| Invoices | `invoices.apply_invoice_coupon` | Apply/remove invoice coupon |
| Invoices | `invoices.return_invoice` | Create a sales return |
| Payments | `payments.process_collection` | Collect customer payment |
| Payments | `payments.refund_payment` | Process payment refund |
| Inventory | `inventory.transfer_stock` | Transfer stock between locations |
| Accounting | `accounting.manage_chart_of_accounts` | Manage chart of accounts / opening balances |
| Accounting | `accounting.post_journal_entry` | Post manual journal entries |
| Accounting | `accounting.close_accounting_period` | Close accounting period |
| Accounting | `accounting.view_financial_reports` | Access financial statements and reports |
| Purchasing | `purchases.confirm_purchase` | Confirm a purchase |
| Purchasing | `purchases.cancel_purchase` | Cancel a purchase |
| Purchasing | `purchases.return_purchase` | Create a purchase return |
| Purchasing | `purchases.process_supplier_payment` | Pay a supplier |

## Inventory reads

Inventory reads are explicit as well:

- `inventory.view_stocklocation`
- `inventory.view_stockbalance`
- `inventory.view_stockmovement`

The migration that introduces these explicit reads automatically grants them to groups that already have `inventory.transfer_stock`, preserving existing transfer-capable roles without reopening broad authenticated-user access.

## Sessions and permission changes

Authentication sessions keep an authorization snapshot in Redis for hot-path permission checks. When a user's direct permissions, group membership, group permissions, or role level changes, active session caches are invalidated. The next request can refresh the session and receives the new effective permission set.

`GET /api/v1/auth/me/` returns the effective permission set and role level so the frontend can align its navigation and route guards with the backend policy.
