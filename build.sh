#!/usr/bin/env bash
# Build step for container hosts (Render, Railway and similar).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Populate the demonstration data on first deploy. Safe to re-run: it only
# creates records that do not already exist.
python manage.py seed
