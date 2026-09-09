#!/usr/bin/env bash
set -euo pipefail

: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${BACKUP_FILE:?BACKUP_FILE is required}"
: "${DB_HOST:=localhost}"
: "${DB_PORT:=5432}"

PGPASSWORD="${DB_PASSWORD:-}" pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --username="$DB_USER" \
  --dbname="$DB_NAME" \
  "$BACKUP_FILE"

echo "Restore completed from $BACKUP_FILE"
