from .base import *

# Dev mode (Cloud Shell)
DEBUG = True

# In dev, allow anything hitting the dev server (adjust if you want stricter)
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]

# Dev-only convenience (optional)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
