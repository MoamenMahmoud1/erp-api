#!/bin/sh
set -eu
# CI-only migration generation. Existing tracked migration directories are
# temporarily moved aside, fresh migrations are generated from current models,
# tests run against that generated graph, and the tracked history is restored.

backup_root="$(mktemp -d)"
manifest="$backup_root/manifest"
cleanup() {
  if [ -f "$manifest" ]; then
    while IFS="$(printf '\t')" read -r app_path backup_path existed; do
      [ -z "$app_path" ] && continue
      rm -rf "$app_path/migrations"
      if [ "$existed" = "1" ]; then
        mkdir -p "$app_path"
        mv "$backup_path" "$app_path/migrations"
      fi
    done < "$manifest"
  fi
  rm -rf "$backup_root"
}
trap cleanup EXIT HUP INT TERM

python - "$backup_root" "$manifest" <<'PY'
import shutil
import sys
from pathlib import Path

import django

django.setup()

from django.conf import settings
from django.apps import apps

root = Path(settings.BASE_DIR).resolve()
backup_root = Path(sys.argv[1])
manifest = Path(sys.argv[2])

with manifest.open("w", encoding="utf-8") as out:
    for app_config in apps.get_app_configs():
        app_path = Path(app_config.path).resolve()
        try:
            app_path.relative_to(root)
        except ValueError:
            continue

        migrations_dir = app_path / "migrations"
        existed = migrations_dir.is_dir()
        backup_path = backup_root / app_config.label
        if existed:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(migrations_dir), str(backup_path))

        migrations_dir.mkdir(parents=True, exist_ok=True)
        (migrations_dir / "__init__.py").write_text("", encoding="utf-8")
        out.write(f"{app_path}\t{backup_path}\t{1 if existed else 0}\n")
PY

python manage.py makemigrations --noinput
"$@"
