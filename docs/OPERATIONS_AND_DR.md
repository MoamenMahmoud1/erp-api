# Operations, monitoring and disaster recovery

## Health probes

Use `/health/live/` for process liveness and `/health/ready/` for readiness. Readiness verifies both PostgreSQL and the configured Django cache backend.

## Request metrics

Every request emits a structured `erp.metrics` log containing method, path, status and duration in milliseconds. Ship these logs to the deployment's logging/monitoring system and alert on sustained latency and 5xx rates.

## Report scaling

The operational dashboard is intentionally live. It does not wait for a Redis report cache or a periodic dashboard refresh, because sales, payments, purchases and stock values can change immediately after a transaction.

Cheap global master-data counts are stored transactionally on the singleton `organization.Company` as `product_count`, `invoice_count`, `customer_count`, and `supplier_count`. Normal create/delete operations update those counters with database-side expressions. A Celery Beat job reconciles them daily at 02:00 UTC so imports, bulk ORM operations, scripts, or other bypasses cannot leave them stale indefinitely.

Celery is not used to keep the dashboard fresh today. It is reserved for materially expensive background work such as multi-year historical analytics, forecasting, and other intelligence calculations that should not execute in request time.

For production, run a dedicated Celery worker and Beat scheduler if the scheduled integrity check is enabled. Redis is the configured broker by default and may be overridden with `CELERY_BROKER_URL`.

## Database backups

Run `scripts/backup_postgres.sh` with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and optional `DB_HOST`, `DB_PORT`, `BACKUP_DIR`. Store dumps outside the application host, encrypt them at rest, and retain multiple recovery points.

To restore, set `BACKUP_FILE` and run `scripts/restore_postgres.sh` against a maintenance database window.

A production deployment should test restores regularly rather than treating a successful dump as proof of recoverability.
