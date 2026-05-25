#!/usr/bin/env bash
# exit on error
set -o errexit

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Start celery worker in the background
# --pool=threads is used to save memory in the free instance
celery -A banking_system worker -l info --pool=threads &

# Start celery beat in the background
celery -A banking_system beat -l info &

# Start the Django Web Server (Gunicorn) in the foreground
gunicorn banking_system.wsgi:application --bind 0.0.0.0:$PORT
