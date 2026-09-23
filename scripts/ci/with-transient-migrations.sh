#!/bin/sh
set -eu

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

python manage.py makemigrations --noinput
"$@"
