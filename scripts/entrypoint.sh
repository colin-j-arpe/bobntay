#!/usr/bin/env bash
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    python manage.py createsuperuser --noinput 2>/dev/null || true
fi

exec gunicorn \
    --workers 2 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    bobntay.wsgi:application
