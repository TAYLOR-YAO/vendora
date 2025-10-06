# backend/vendora_backend/settings/base.py
import os
from pathlib import Path
from datetime import timedelta
from corsheaders.defaults import default_headers, default_methods  # <-- keep

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",") if h]
CSRF_TRUSTED_ORIGINS = [s.strip() for s in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if s.strip()]

INSTALLED_APPS = [
    "core",
    "identity.apps.IdentityConfig",
    "taxonomy",
    "business",
    "crm",
    "commerce.apps.CommerceConfig",
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
    "platformapp",

    # third-party
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "drf_spectacular",
    "workflow",
    "billing",
    "searchapp",

    # contrib
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

APPEND_SLASH = True


SITE_ID = 1
AUTH_USER_MODEL = "identity.User"

AUTHENTICATION_BACKENDS = (
    "allauth.account.auth_backends.AuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
        # WhiteNoise can be below CORS; it only serves /static
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.middleware.DevCORSPreflightMiddleware",   # <— add
    "core.middleware.RequestIDMiddleware",          # <— add
    "core.middleware.TimingMiddleware",             # <— add
    # ⬇️ Put CORS as high as possible
    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "vendora_backend.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "vendora_backend.wsgi.application"

# DB (unchanged)
if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "vendora"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST"),
            "PORT": int(os.getenv("POSTGRES_PORT", "5432")),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(BASE_DIR / "db.sqlite3")}}

LANGUAGE_CODE = "en-us"; TIME_ZONE = "UTC"; USE_I18N = True; USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Proxies/redirects
APPEND_SLASH = False
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# DRF
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "600/minute",
    },
}
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append("rest_framework.renderers.BrowsableAPIRenderer")

SPECTACULAR_SETTINGS = {"TITLE": "Vendora API", "DESCRIPTION": "Multipurpose Marketplace + CRM API", "VERSION": "0.2.0"}

# auth
REST_USE_JWT = True
REST_SESSION_LOGIN = False
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"

REST_AUTH = {
    "USE_JWT": True,
    "SESSION_LOGIN": False,
    "JWT_AUTH_COOKIE": "vendora-auth",
    "JWT_AUTH_REFRESH_COOKIE": "vendora-refresh-token",
    "REGISTER_SERIALIZER": "identity.serializers.UserSerializer",
    "USER_DETAILS_SERIALIZER": "identity.serializers.UserDetailsSerializer",
}

DJ_REST_AUTH = {"USE_JWT": True, "SESSION_LOGIN": False}

# SimpleJWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}

SESSION_ENGINE = "django.contrib.sessions.backends.db"

LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django": {"handlers": ["console"], "level": "INFO"},
                "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False}},
}

OPENSEARCH = {
    "URL": os.getenv("OPENSEARCH_URL", ""),
    "USER": os.getenv("OPENSEARCH_USER", ""),
    "PASS": os.getenv("OPENSEARCH_PASS", ""),
}

# media for saved models
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"


# Campaign defaults
CAMPAIGN_DEFAULT_CHUNK_SIZE = int(os.getenv("CAMPAIGN_DEFAULT_CHUNK_SIZE", "500"))

# settings.py (add to CELERY_BEAT_SCHEDULE)
CELERY_BEAT_SCHEDULE = {
    "popularity-every-15m": {
        "task": "analyticsapp.tasks.rebuild_popularity",
        "schedule": 900,
        "args": ("<TENANT_ID>",),
    },
    "covisitation-hourly": {
        "task": "analyticsapp.tasks.rebuild_covisitation",
        "schedule": 3600,
        "args": ("<TENANT_ID>",),
    },
}


# CORS ⬇︎ (make sure these are present)
CORS_ALLOW_ALL_ORIGINS = True           # dev convenience
CORS_ALLOW_CREDENTIALS = False
CORS_ALLOW_HEADERS = list(default_headers) + ["authorization", "content-type", "accept"]
CORS_EXPOSE_HEADERS = ["Location"]  
CORS_ALLOW_METHODS = list(default_methods)
CORS_URLS_REGEX = r"^/.*$"              # apply to all paths including /api/token/
