from django.apps import apps
from django.utils.module_loading import import_string
from rest_framework import serializers, viewsets, permissions, routers
from common.mixins import TenantScopedModelViewSet
from common.permissions import IsTenantUser

def safe_import(dotted: str):
    try:
        return import_string(dotted)
    except Exception:
        return None

def build_serializer(model):
    # Build via `type` to avoid class-body scope issues
    attrs = {"Meta": type("Meta", (), {"model": model, "fields": "__all__"})}
    cls = type(f"{model.__name__}AutoSerializer", (serializers.ModelSerializer,), attrs)
    return cls

def get_model_serializer(model):
    dotted = f"{model._meta.app_label}.serializers.{model.__name__}Serializer"
    cls = safe_import(dotted)
    return cls or build_serializer(model)

def build_viewset(model):
    serializer_cls = get_model_serializer(model)
    attrs = {
        "queryset": model.objects.all(),
        "serializer_class": serializer_cls,
        "permission_classes": [IsTenantUser],
    }
    cls = type(f"{model.__name__}AutoViewSet", (TenantScopedModelViewSet,), attrs)
    return cls

def build_app_router(app_label: str):
    router = routers.DefaultRouter()
    for model in apps.get_app_config(app_label).get_models():
        vs = build_viewset(model)
        base = model._meta.model_name.replace("_","-")
        router.register(base, vs, basename=f"{app_label}-{base}")
    return router
# backend/common/api_auto.py
from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Read-only for everyone (GET, HEAD, OPTIONS).
    Write access (POST, PUT, PATCH, DELETE) only for staff/admin users.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission: user must be the owner or an admin.
    Falls back to read-only for everyone.
    """

    def has_object_permission(self, request, view, obj):
        # Always allow read-only methods
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admins always allowed
        if request.user and request.user.is_staff:
            return True

        # Check object ownership if it has a "user" or "owner" attribute
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "owner"):
            return obj.owner == request.user

        return False


class IsTenantAdminOrReadOnly(permissions.BasePermission):
    """
    Read-only for all users. Write access restricted to tenant admins.
    This assumes request.user has 'is_staff' or a tenant-admin flag.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        # If user has staff flag or role = tenant_admin
        return getattr(user, "is_staff", False) or getattr(user, "is_tenant_admin", False)


__all__ = [
    "IsAdminOrReadOnly",
    "IsOwnerOrAdmin",
    "IsTenantAdminOrReadOnly",
]
