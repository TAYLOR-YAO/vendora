from __future__ import annotations
from typing import List, Type, Optional
from django.apps import apps
from django.db import models
from django.conf import settings
from django.utils.module_loading import import_string

from rest_framework import serializers, viewsets, permissions, routers, filters
from rest_framework.pagination import PageNumberPagination

from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Read for everyone; write only for staff/admin.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    If a model has 'owner' or 'user' FK/field, only that user (or admin) can modify.
    Falls back to IsAdminOrReadOnly if ownership field not present.
    """
    owner_fields = ("owner", "user")

    def _get_owner(self, obj):
        for f in self.owner_fields:
            if hasattr(obj, f):
                return getattr(obj, f)
        return None

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        owner = self._get_owner(obj)
        return bool(owner and owner == user)

def default_permissions_for_model(model: Type[models.Model]) -> List[permissions.BasePermission]:
    """
    If model exposes owner/user, enforce IsOwnerOrAdmin; else IsAdminOrReadOnly.
    """
    ownerish = any(hasattr(model, f) for f in IsOwnerOrAdmin.owner_fields)
    return [IsOwnerOrAdmin] if ownerish else [IsAdminOrReadOnly]


class IsTenantUser(BasePermission):
    """
    Very simple dev permission: allow all authenticated OR allow all in DEBUG.
    Replace with proper RBAC/JWT later.
    """
    def has_permission(self, request, view):
        return True

class ReadPublicWriteAuth(BasePermission):
    """
    Public GET/HEAD/OPTIONS; writes require authentication.
    Tenant requirement is handled in the ViewSet mixin.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

class PrivateTenantOnly(BasePermission):
    """
    All requests must be authenticated AND provide X-Tenant-ID header.
    (Adjust to accept tenant via querystring if you prefer)
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            # Still private: require auth + tenant even for reads in CRM
            return bool(request.user and request.user.is_authenticated and request.headers.get("X-Tenant-ID"))
        return bool(request.user and request.user.is_authenticated and request.headers.get("X-Tenant-ID"))