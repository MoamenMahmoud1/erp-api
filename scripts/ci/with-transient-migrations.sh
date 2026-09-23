#!/bin/sh
set -eu

cleanup() {
  rm -f authsession/migrations/[0-9]*.py
  rm -f authsession/migrations/[0-9]*.pyc
  rm -rf authsession/migrations/__pycache__
  rmdir authsession/migrations 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

python manage.py makemigrations authsession --noinput
"$@"
