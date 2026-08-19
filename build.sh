#!/usr/bin/env bash
# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput || echo "Superuser already exists."
fi
