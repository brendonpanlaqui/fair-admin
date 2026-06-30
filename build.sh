#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Compress and collect your CSS/JS admin assets
python manage.py collectstatic --no-input

# Sync your cloud database models
python manage.py migrate

# automatically create the superuser if it doesn't exist
python manage.py createsuperuser --noinput || true