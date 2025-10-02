from .base import *
import os

# Respect env override, default to False in prod
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"

# Allow Cloud Run hostnames; for custom domain, set ALLOWED_HOSTS via env.
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]

# Broad wildcard for Cloud Run (you can tighten later with your exact URL):
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        "https://*.a.run.app",
        "https://*.run.app",
    ]

# Required behind Cloud Run’s proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Keep cookies secure in prod
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
