# backend/vendora_backend/settings/dev.py
from .base import *

DEBUG = True

# Put our dev preflight middleware at the VERY TOP
MIDDLEWARE = [
    "core.middleware.DevCORSPreflightMiddleware",
] + MIDDLEWARE

ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1"]

# The frontend origin
FRONTEND_ORIGIN = "https://3002-cs-225507065464-default.cs-us-east1-pkhd.cloudshell.dev"
# The backend origin (where the API is served)
BACKEND_ORIGIN = "https://8080-cs-225507065464-default.cs-us-east1-pkhd.cloudshell.dev"

CSRF_TRUSTED_ORIGINS = [
    "https://*.cloudshell.dev",
    FRONTEND_ORIGIN,
    BACKEND_ORIGIN,
]

# Use a specific allow-list for CORS instead of allowing all origins.
CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN, BACKEND_ORIGIN]

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(BASE_DIR / "db.sqlite3")}
}
