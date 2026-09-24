# Payment lifecycle

Customer collections support cash and bank transfer components.

## Cash

Cash is effective immediately when the collection is recorded. The collection posts the cash debit and accounts-receivable credit and contributes to the invoice's paid balance.

## Bank transfer

A bank transfer is recorded as **pending** until an authorized user explicitly accepts it.

While pending:

- The transfer remains visible on the payment transaction.
- It does not contribute to the invoice paid balance.
- It does not contribute to the effective refundable balance.
- It does not post a bank/accounting entry.
- A mixed cash + transfer collection only makes the cash component effective.

Approval is exposed through:

`POST /api/v1/payments/transactions/<id>/approve-transfer/`

After approval:

- The transfer becomes effective for invoice balances.
- A dedicated `payment.transfer.approval` journal entry debits Bank and credits Accounts Receivable.
- Any invoice that is fully paid by the now-effective amount moves to `paid`.
- Repeating the approval request is idempotent: an already-approved transfer returns its existing transaction state without creating another financial journal.

The approval flow locks the payment transaction and affected invoices before checking balances, preventing concurrent approvals from creating an overpayment.

The approval state is derived from the posted approval journal rather than a new database status column. This preserves the repository's current migrationless schema strategy while keeping the acceptance event durable and auditable.
