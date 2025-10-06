# This file was auto-generated as a scaffold.
# SAFE to edit. Keep functions/class names if you rely on them across apps.

from typing import Any, Dict
from django.db import transaction

@transaction.atomic
def upsert(instance, data: Dict[str, Any], *, save=True):
    """Populate fields on an existing instance; optionally save."""
    for k, v in data.items():
        setattr(instance, k, v)
    if save:
        instance.save()
    return instance

@transaction.atomic
def create(model, data: Dict[str, Any]):
    return model.objects.create(**data)
