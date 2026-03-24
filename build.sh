#!/usr/bin/env bash
# exit on error
set -o errexit

echo "=== Step 1: pip upgrade ==="
pip install --upgrade pip

echo "=== Step 2: pip install requirements ==="
pip install -r requirements.txt

echo "=== Step 3: collectstatic ==="
python manage.py collectstatic --no-input

echo "=== Build completed successfully! ==="
