import os
from pathlib import Path
import logging

# Project root (…/vendora_backend/settings/base.py -> BASE_DIR = repo root)
BASE_DIR = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------
# Core flags
# ---------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"

# ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS can be set via env, else empty.
# In prod.py we’ll set sane defaults for Cloud Run wildcards.
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [u.strip() for u in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if u.strip()]

# Always set secure cookies (Cloud Run is HTTPS). If you truly need non-HTTPS in dev,
# override these in dev.py.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ---------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    # 3rd party
    "corsheaders",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party REST tooling
    "rest_framework",
    "drf_spectacular",

    # Vendora apps
    "core",
    "platformapp",
    "identity",
    "taxonomy",
    "business",
    "crm",
    "commerce",
    "payments",
    "inventory",
    "shipments",
    "hr",
    "invoicing",
    "appointments",
    "notificationsapp",
    "support",
    "marketing",
    "analyticsapp",
    "aiapp",
]

# ---------------------------------------------------------------------
# Middleware (ORDER MATTERS)
# - WhiteNoise must be RIGHT AFTER SecurityMiddleware
# - Messages/CSRF/auth are necessary for admin login flow
# ---------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",           # <- move here
    "corsheaders.middleware.CorsMiddleware",                # optional, harmless without config
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "vendora_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # add template dirs if you have custom templates
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# DB-backed sessions (needed for admin)
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ---------------------------------------------------------------------
# Logging:
# - Print request exceptions (500s) to console
# - Include csrf/security noise for debugging POST issues
# - Gunicorn error logger gets tied in by propagate=True
# ---------------------------------------------------------------------
LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {},
    "formatters": {
        "simple": {"format": "[%(levelname)s] %(name)s: %(message)s"},
        "verbose": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django.security.csrf": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "gunicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": True},
        # add app-specific loggers here as needed
    },
}

WSGI_APPLICATION = "vendora_backend.wsgi.application"

# ---------------------------------------------------------------------
# Database
# - If POSTGRES_HOST is set -> Postgres (Cloud SQL via connector)
# - Else -> SQLite (great for Cloud Shell dev at zero cost)
# ---------------------------------------------------------------------
if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "vendora"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST"),  # e.g. /cloudsql/<project>:<region>:<instance>
            "PORT": int(os.getenv("POSTGRES_PORT", "5432")),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
    }

# ---------------------------------------------------------------------
# i18n / TZ
# ---------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------
# Static files (Cloud Run + WhiteNoise)
# ---------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------
# DRF / Spectacular
# ---------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Vendora API",
    "DESCRIPTION": "Multipurpose Marketplace + CRM API",
    "VERSION": "0.2.0",
}
