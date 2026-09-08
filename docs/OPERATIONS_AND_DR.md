# Operations, monitoring and disaster recovery

## Health probes

Use `/health/live/` for process liveness and `/health/ready/` for readiness. Readiness verifies both PostgreSQL and the configured Django cache backend.

## Request metrics

Every request emits a structured `erp.metrics` log containing method, path, status and duration in milliseconds. Ship these logs to the deployment's logging/monitoring system and alert on sustained latency and 5xx rates.

## Report scaling

Management reports use a short Redis-backed cache controlled by `REPORT_CACHE_TTL` (default 30 seconds). The `warm_reports` management command can be scheduled from cron/systemd/Kubernetes to pre-populate common dashboard reports.

## Database backups

Run `scripts/backup_postgres.sh` with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and optional `DB_HOST`, `DB_PORT`, `BACKUP_DIR`. Store dumps outside the application host, encrypt them at rest, and retain multiple recovery points.

To restore, set `BACKUP_FILE` and run `scripts/restore_postgres.sh` against a maintenance database window.

A production deployment should test restores regularly rather than treating a successful dump as proof of recoverability.
