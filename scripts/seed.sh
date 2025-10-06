#!/usr/bin/env bash
set -euo pipefail

# This script runs the main Django management command to seed the database.
# All data generation logic is contained within the Python command for
# robustness and maintainability.

echo "==> Executing Django seed_data command..."
python backend/manage.py seed_data
echo "==> Seeding script finished."