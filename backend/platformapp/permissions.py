# backend/platformapp/permissions.py
from __future__ import annotations
from typing import Optional

from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.contrib.auth.models import AnonymousUser

from platformapp.models import UserRole, Role


# --------------------------
# Helpers
# --------------------------
def get_request_tenant_id(request) -> Optional[str]:
    """
    Standard way to read the tenant from the request.
    - Prefer X-Tenant-ID header
    - Fallback to ?tenant= query param
    - Fallback to user.tenant_id if your User model carries it
    """
    tid = (
        request.META.get("HTTP_X_TENANT_ID")
        or request.query_params.get("tenant")
        or getattr(getattr(request, "user", None), "tenant_id", None)
    )
    return str(tid) if tid else None


def _has_role(user, tenant_id: str, role_names: set[str] | None = None,
              scope_levels: set[str] | None = None) -> bool:
    """
    Check if a user has at least one of the given role names and/or scope levels
    for the tenant.
    """
    if not user or isinstance(user, AnonymousUser) or not tenant_id:
        return False
    qs = (
        UserRole.objects
        .select_related("role", "tenant")
        .filter(tenant_id=tenant_id, user_id=getattr(user, "id", None))
    )
    if role_names:
        qs = qs.filter(role__name__in=role_names)
    if scope_levels:
        qs = qs.filter(role__scope_level__in=scope_levels)
    return qs.exists()


def _is_tenant_admin(user, tenant_id: str) -> bool:
    # Treat Django staff as super admin
    if getattr(user, "is_staff", False):
        return True
    # Admin/Owner or scope level "tenant" are considered tenant admins
    return _has_role(user, tenant_id, role_names={"admin", "owner"}, scope_levels={"tenant"})


def _is_tenant_operator(user, tenant_id: str) -> bool:
    # Operator-like roles: manager, operator, staff, editor etc.
    # You can tailor these names to your Role seeds.
    names = {"manager", "operator", "staff", "editor"}
    scopes = {"business", "store"}  # operators usually at business/store scope
    return _has_role(user, tenant_id, role_names=names, scope_levels=scopes)


def _is_tenant_member(user, tenant_id: str) -> bool:
    # Any role record for this tenant qualifies as a "member"
    return _has_role(user, tenant_id)


# --------------------------
# Permissions
# --------------------------
class IsTenantAdminOrReadOnly(BasePermission):
    """
    SAFE_METHODS → allowed to everyone.
    Mutations → require tenant admin (or Django staff).
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        tenant_id = get_request_tenant_id(request)
        return _is_tenant_admin(request.user, tenant_id)


class IsTenantOperatorOrAdmin(BasePermission):
    """
    SAFE_METHODS → allowed to everyone (you can tighten to members by changing below).
    Mutations → require operator or admin for the tenant.
    """
    allow_read_only_to_anyone = True  # flip to False if you want reads limited to members

    def has_permission(self, request, view):
        tenant_id = get_request_tenant_id(request)

        if request.method in SAFE_METHODS:
            if self.allow_read_only_to_anyone:
                return True
            # else require at least membership to read:
            return _is_tenant_member(request.user, tenant_id)

        # write ops
        return _is_tenant_admin(request.user, tenant_id) or _is_tenant_operator(request.user, tenant_id)


class IsTenantMemberOrReadOnly(BasePermission):
    """
    SAFE_METHODS → allowed to everyone.
    Mutations → require *any* membership on the tenant.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        tenant_id = get_request_tenant_id(request)
        return _is_tenant_member(request.user, tenant_id)


class HasTenantContext(BasePermission):
    """
    Require a tenant context (header or query) for any request (read or write).
    Useful for endpoints that must always be tenant-bound.
    """
    def has_permission(self, request, view):
        return get_request_tenant_id(request) is not None
