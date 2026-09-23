#!/bin/sh
set -eu
# CI-only schema generation: missing migration packages and generated
# migration files exist only for the duration of this process.

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
import django
django.setup()

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

python manage.py makemigrations --noinput
"$@"
