#!/usr/bin/env python
import os
import sys

# Default to dev settings locally; on Cloud Run set DJANGO_SETTINGS_MODULE=vendora_backend.settings.prod
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv(
    "DJANGO_SETTINGS_MODULE", "vendora_backend.settings.dev"
))

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    execute_from_command_line(sys.argv)
