# Operations, monitoring and disaster recovery

## Health probes

Use `/health/live/` for process liveness and `/health/ready/` for readiness. Readiness verifies both PostgreSQL and the configured Django cache backend.

## Request metrics

Every request emits a structured `erp.metrics` log containing method, path, status and duration in milliseconds. Ship these logs to the deployment's logging/monitoring system and alert on sustained latency and 5xx rates.

## Report scaling

Management reports use a short Redis-backed cache controlled by `REPORT_CACHE_TTL` (default 30 seconds). The `accounting.tasks.warm_analytics_reports` Celery task can pre-populate the standard dashboard window, and Celery Beat schedules it every 15 minutes. Report calculations remain in `accounting/services/` and are reused by HTTP endpoints and background jobs.

Product intelligence uses its own one-hour cache and is refreshed by `products.tasks.refresh_product_intelligence` every hour through Celery Beat.

For production, run at least one dedicated Celery worker and one Beat scheduler process alongside the web application. Redis is the configured broker by default and may be overridden with `CELERY_BROKER_URL`.

## Database backups

Run `scripts/backup_postgres.sh` with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and optional `DB_HOST`, `DB_PORT`, `BACKUP_DIR`. Store dumps outside the application host, encrypt them at rest, and retain multiple recovery points.

To restore, set `BACKUP_FILE` and run `scripts/restore_postgres.sh` against a maintenance database window.

A production deployment should test restores regularly rather than treating a successful dump as proof of recoverability.
