"""
Dynamic API builder:
- Creates ModelSerializer + ModelViewSet per model at runtime (unless custom exists).
- Registers them on a DRF router under /api/v1/<app>/<model>/
"""
from typing import Optional
from django.apps import apps
from django.utils.module_loading import import_string
from rest_framework import serializers, viewsets, permissions, routers
from common.permissions import IsTenantUser
from common.mixins import TenantScopedModelViewSet

def _try(dotted: str) -> Optional[type]:
    try:
        return import_string(dotted)
    except Exception:
        return None

def build_serializer(model):
    # Prefer app-defined <Model>Serializer if present
    custom = _try(f"{model._meta.app_label}.serializers.{model.__name__}Serializer")
    if custom:
        return custom
    Meta = type("Meta", (), {"model": model, "fields": "__all__"})
    return type(f"{model.__name__}AutoSerializer", (serializers.ModelSerializer,), {"Meta": Meta})

def build_viewset(model):
    # Prefer app-defined <Model>ViewSet if present
    custom = _try(f"{model._meta.app_label}.views.{model.__name__}ViewSet")
    if custom:
        return custom
    serializer = build_serializer(model)
    attrs = {
        "queryset": model.objects.all(),
        "serializer_class": serializer,
        "permission_classes": [IsTenantUser], # Use the actual permission class
    }
    return type(f"{model.__name__}AutoViewSet", (TenantScopedModelViewSet,), attrs)

def build_router_for_app(app_label: str) -> routers.DefaultRouter:
    router = routers.DefaultRouter()
    for model in apps.get_app_config(app_label).get_models():
        base = model._meta.model_name.replace("_", "-")
        router.register(base, build_viewset(model), basename=f"{app_label}-{base}")
    return router
