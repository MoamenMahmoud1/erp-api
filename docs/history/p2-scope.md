# P2 accounting scope

The current ERP domain is a sales, purchases, inventory, payments and core-accounting backend. P2 hardening now covers historical inventory valuation, report scaling, request telemetry, cache/dependency readiness, database recovery tooling, and background report/intelligence jobs.

Advanced accounting capabilities such as VAT/tax engines, multi-currency, bank reconciliation, fixed assets, and analytic accounting dimensions are not correctness fixes to the current domain. They should be added as separate modules when a concrete business requirement exists, rather than introducing partial implementations that change the accounting model without a defined requirement.
