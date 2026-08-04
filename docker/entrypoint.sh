#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py import_exercises
python manage.py collectstatic --noinput
exec "$@"

