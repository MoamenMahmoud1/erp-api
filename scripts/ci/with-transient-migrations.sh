#!/bin/sh
set -eu

cleanup() {
  find . -type f -path '*/migrations/[0-9]*.py' -delete
  find . -type f -path '*/migrations/[0-9]*.pyc' -delete
}
trap cleanup EXIT HUP INT TERM

python manage.py makemigrations --noinput
"$@"
