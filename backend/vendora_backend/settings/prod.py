from .base import *
import os

DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h] or ["*"]

CORS_ALLOW_ALL_ORIGINS = DEBUG 
# Typical Cloud Run hosts (override via env)
CSRF_TRUSTED_ORIGINS = [
    s.strip() for s in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "https://*.run.app,https://*.a.run.app"
    ).split(",") if s.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# In prod, set explicit CORS_ALLOWED_ORIGINS via env
