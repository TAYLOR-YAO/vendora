import os

from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
# This should match your project's settings path.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vendora_backend.settings.dev")

app = Celery("vendora_backend")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# backend/vendora_backend/celery.py or wherever you define beat_schedule
from celery.schedules import crontab

app.conf.beat_schedule.update({
    "autolabel-tenant-<TENANT_ID>-nightly": {
        "task": "aiapp.tasks.autolabel_payments",
        "schedule": crontab(minute=15, hour=2),  # 02:15 UTC nightly
        "args": ["<TENANT_UUID>", 7],
    },
    "train-fraud-tenant-<TENANT_ID>-nightly": {
        "task": "aiapp.tasks.train_fraud_model",
        "schedule": crontab(minute=45, hour=2),  # train after labels
        "args": ["<TENANT_UUID>", 200],
    },
})
