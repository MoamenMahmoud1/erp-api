#!/usr/bin/env bash
set -euo pipefail

: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"
: "${BACKUP_DIR:=./backups}"

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_DIR/${DB_NAME}_${timestamp}.dump"

PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --username="$DB_USER" \
  --file="$out" \
  "$DB_NAME"

echo "Backup written to $out"
