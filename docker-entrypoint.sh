#!/usr/bin/env bash
# Copyright (c) 2024 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)
set -e

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Applying database migrations..."
python manage.py migrate

echo "Creating superuser if it doesn't exist..."
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput || echo "Superuser already exists."
else
    echo "No superuser credentials provided, skipping."
fi

echo "Starting server..."
exec "$@"
