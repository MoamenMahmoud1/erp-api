#!/bin/sh
set -eu
# CI-only schema generation: generated migration files and missing migration
# packages are removed on exit. No migration history is committed by CI.

before_files="$(mktemp)"
before_dirs="$(mktemp)"

cleanup() {
  after_files="$(mktemp)"
  after_dirs="$(mktemp)"
  find . -type f -path '*/migrations/[0-9]*.py' -print | sort > "$after_files"
  find . -type d -path '*/migrations' -print | sort > "$after_dirs"

  comm -13 "$before_files" "$after_files" | while IFS= read -r file; do
    [ -z "$file" ] || rm -f "$file"
  done

  comm -13 "$before_dirs" "$after_dirs" | while IFS= read -r directory; do
    [ -z "$directory" ] || rm -rf "$directory"
  done

  rm -f "$before_files" "$before_dirs" "$after_files" "$after_dirs"
}
trap cleanup EXIT HUP INT TERM

find . -type f -path '*/migrations/[0-9]*.py' -print | sort > "$before_files"
find . -type d -path '*/migrations' -print | sort > "$before_dirs"

python - <<'PY'
from pathlib import Path

from django.apps import apps

for app_config in apps.get_app_configs():
    if not app_config.models:
        continue
    migrations_dir = Path(app_config.path) / "migrations"
    if migrations_dir.exists():
        continue
    migrations_dir.mkdir()
    (migrations_dir / "__init__.py").write_text("", encoding="utf-8")
PY

python - <<'PY'
from django.apps import apps

for app_config in apps.get_app_configs():
    if app_config.models:
        print(
            "CI_MIGRATION_APP",
            app_config.label,
            "module=" + app_config.name,
            "path=" + app_config.path,
            "migrations=" + repr(app_config.migrations_module()),
        )
PY

python manage.py makemigrations --noinput --verbosity 2
python manage.py showmigrations --verbosity 1
"$@"
