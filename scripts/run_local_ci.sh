#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python}"
LOG_FILE="${LOG_FILE:-local-ci-output.log}"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-core.settings.settings_test}"
export SECRET_KEY="${SECRET_KEY:-local-test-secret-key-not-for-production}"
export JWT_SIGNING_KEY="${JWT_SIGNING_KEY:-local-test-jwt-signing-key-0123456789abcdef0123456789abcdef}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-testserver,localhost,127.0.0.1}"
export CORS_ALLOWED_ORIGINS="${CORS_ALLOWED_ORIGINS:-http://localhost:3000}"
export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-http://localhost:3000}"
export DB_NAME="${DB_NAME:-erp_api_test}"
export DB_USER="${DB_USER:-erp_api}"
export DB_PASSWORD="${DB_PASSWORD:-local-development-only}"
export DB_HOST="${DB_HOST:-127.0.0.1}"
export DB_PORT="${DB_PORT:-5432}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

: > "$LOG_FILE"
FAILED=0

run_step() {
    local label="$1"
    shift
    local -a command=("$@")

    printf '\n%s\n' "============================================================" | tee -a "$LOG_FILE"
    printf ' %s\n' "$label" | tee -a "$LOG_FILE"
    printf '%s\n' "============================================================" | tee -a "$LOG_FILE"
    printf '$' | tee -a "$LOG_FILE"
    for arg in "${command[@]}"; do printf ' %q' "$arg" | tee -a "$LOG_FILE"; done
    printf '\n' | tee -a "$LOG_FILE"

    if "${command[@]}" 2>&1 | tee -a "$LOG_FILE"; then
        printf '\n[PASS] %s\n' "$label" | tee -a "$LOG_FILE"
    else
        printf '\n[FAIL] %s\n' "$label" | tee -a "$LOG_FILE"
        FAILED=$((FAILED + 1))
    fi
}

printf 'ERP API local verification\n' | tee -a "$LOG_FILE"
printf 'Working directory: %s\n' "$ROOT_DIR" | tee -a "$LOG_FILE"
printf 'Django settings: %s\n' "$DJANGO_SETTINGS_MODULE" | tee -a "$LOG_FILE"
printf 'Database: %s@%s:%s/%s\n' "$DB_USER" "$DB_HOST" "$DB_PORT" "$DB_NAME" | tee -a "$LOG_FILE"
printf 'Log file: %s\n' "$LOG_FILE" | tee -a "$LOG_FILE"

run_step "Python version" "$PYTHON" --version
run_step "Django checks" "$PYTHON" manage.py check
run_step "Migration drift check" "$PYTHON" manage.py makemigrations --check --dry-run

printf '\n%s\n' "============================================================" | tee -a "$LOG_FILE"
printf ' Ruff (informational)\n' | tee -a "$LOG_FILE"
printf '%s\n' "============================================================" | tee -a "$LOG_FILE"
if ruff check . 2>&1 | tee -a "$LOG_FILE"; then
    printf '\n[PASS] Ruff\n' | tee -a "$LOG_FILE"
else
    printf '\n[INFO] Ruff reported existing lint debt; it is not part of P0-P2 verification.\n' | tee -a "$LOG_FILE"
fi

run_step "P0/P1 focused tests" "$PYTHON" manage.py test \
    accounting.tests.test_permissions \
    accounting.tests.test_reconciliation \
    accounting.tests.test_balances \
    inventory.tests.test_permissions \
    inventory.tests.test_valuation \
    authsession.tests.test_permission_invalidation \
    accounts.tests.test_current_user_permissions \
    organization.tests.test_metrics \
    core.tests.test_celery \
    auditlog \
    --verbosity 2

run_step "Authentication suite" "$PYTHON" manage.py test accounts authsession authentication --verbosity 1
run_step "Organization suite" "$PYTHON" manage.py test organization customers suppliers --verbosity 1
run_step "Catalog suite" "$PYTHON" manage.py test products coupons --verbosity 1
run_step "Sales suite" "$PYTHON" manage.py test invoices payments inventory --verbosity 1
run_step "Purchasing suite" "$PYTHON" manage.py test purchases --verbosity 1
run_step "Accounting suite" "$PYTHON" manage.py test accounting auditlog --verbosity 1
run_step "Infrastructure suite" "$PYTHON" manage.py test core common --verbosity 1

# Production settings use the real PostgreSQL connection pool and may require
# a real production-style database/Redis environment. Keep this opt-in for
# local development instead of hanging against a destroyed Django test DB.
if [[ "${CHECK_PRODUCTION:-0}" == "1" ]]; then
    export DJANGO_SETTINGS_MODULE="core.settings.settings_prod"
    export SECRET_KEY="${SECRET_KEY_PROD_CHECK:-local-production-check-secret}"
    export JWT_SIGNING_KEY="${JWT_SIGNING_KEY_PROD_CHECK:-local-production-jwt-signing-key-0123456789abcdef0123456789abcdef}"
    export ALLOWED_HOSTS="${ALLOWED_HOSTS_PROD_CHECK:-example.com}"
    export CORS_ALLOWED_ORIGINS="${CORS_ALLOWED_ORIGINS_PROD_CHECK:-https://example.com}"
    export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS_PROD_CHECK:-https://example.com}"
    export DB_NAME="${DB_NAME_PROD_CHECK:-$DB_NAME}"
    export DB_USER="${DB_USER_PROD_CHECK:-$DB_USER}"
    export DB_PASSWORD="${DB_PASSWORD_PROD_CHECK:-$DB_PASSWORD}"
    export DB_HOST="${DB_HOST_PROD_CHECK:-$DB_HOST}"
    export DB_PORT="${DB_PORT_PROD_CHECK:-$DB_PORT}"
    export REDIS_URL="${REDIS_URL_PROD_CHECK:-$REDIS_URL}"
    export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
    export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
    export AWS_STORAGE_BUCKET_NAME="${AWS_STORAGE_BUCKET_NAME:-}"
    run_step "Production Django deploy checks" "$PYTHON" manage.py check --deploy --fail-level ERROR
else
    printf '\n[SKIP] Production Django deploy checks (set CHECK_PRODUCTION=1 to run).\n' | tee -a "$LOG_FILE"
fi

if [[ "${CHECK_FRONTEND:-1}" == "1" && -f frontend/package.json ]]; then
    if command -v npm >/dev/null 2>&1; then
        if [[ -f frontend/package-lock.json ]]; then
            run_step "Frontend install" bash -lc 'cd frontend && npm ci --no-audit --no-fund'
        else
            run_step "Frontend install" bash -lc 'cd frontend && npm install --no-audit --no-fund'
        fi
        run_step "Frontend build" bash -lc 'cd frontend && npm run build'
    else
        printf '\n[SKIP] Frontend checks: npm is not installed.\n' | tee -a "$LOG_FILE"
    fi
fi

printf '\n%s\n' "============================================================" | tee -a "$LOG_FILE"
printf 'FINAL RESULT\n' | tee -a "$LOG_FILE"
printf '%s\n' "============================================================" | tee -a "$LOG_FILE"
if [[ "$FAILED" -eq 0 ]]; then
    printf '[PASS] All required local CI checks passed.\n' | tee -a "$LOG_FILE"
    exit 0
fi

printf '[FAIL] %d required check group(s) failed.\n' "$FAILED" | tee -a "$LOG_FILE"
printf 'Full output: %s\n' "$LOG_FILE" | tee -a "$LOG_FILE"
exit 1
