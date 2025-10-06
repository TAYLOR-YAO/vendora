# backend/common/mixins.py
from __future__ import annotations

from typing import Iterable, Dict, Any, Optional
from django.db.models import Q, Model
from django.core.exceptions import FieldDoesNotExist
from django.utils.timezone import now
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework import viewsets
from django.db.models import QuerySet

# -----------------------------
# Pagination
# -----------------------------
class DefaultPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


# -----------------------------
# Base tenant-scoped MVSet
# -----------------------------
class TenantScopedModelViewSet(ModelViewSet):
    """
    Opinionated, multi-tenant base ViewSet:

    - Reads tenant from `X-Tenant-ID` header or `?tenant=` query param.
    - If tenant is present, auto-filters queryset by `<tenant_field>_id=...`.
    - If tenant is missing:
        * By default: reads (GET/HEAD/OPTIONS) -> returns empty set; writes -> forbidden.
        * If `allow_public_list` is True and action is list, falls back to `public_filters`.
    - Adds simple "q" search (icontains across `search_fields`) and "order" (comma-separated).
    - Applies simple exact filters from query params that match model fields.

    Override:
      - `tenant_field` (default "tenant")
      - `allow_public_list` (default False)
      - `public_filters` (dict of filters for public lists, default {"is_public": True, "is_active": True})
      - `search_fields` (tuple of field names)
      - `ordering_fields` (tuple of field names allowed for ordering)
      - `default_ordering` (sequence)
    """
    pagination_class = DefaultPagination

    tenant_header = "HTTP_X_TENANT_ID"
    tenant_query_param = "tenant"
    tenant_field = "tenant"

    allow_public_list = False
    public_filters: Dict[str, Any] = {"is_public": True, "is_active": True}

    search_fields: Iterable[str] = tuple()
    ordering_fields: Iterable[str] = tuple()
    default_ordering: Iterable[str] = ("-created_at",)

    # ---- Tenant helpers ----
    def get_tenant_id(self) -> Optional[str]:
        req = self.request
        tid = req.META.get(self.tenant_header) or req.query_params.get(self.tenant_query_param)
        return str(tid) if tid else None

    # ---- Queryset plumbing ----
    def _model_class(self) -> type[Model]:
        if hasattr(self, "queryset") and self.queryset is not None:
            return self.queryset.model
        # Fallback to serializer meta
        return self.get_serializer().Meta.model  # type: ignore[attr-defined]

    def _has_field(self, field_name: str) -> bool:
        try:
            self._model_class()._meta.get_field(field_name)
            return True
        except FieldDoesNotExist:
            return False

    def _apply_public_filters(self, qs):
        """Apply only the keys that exist on the model."""
        filters = {}
        for k, v in (self.public_filters or {}).items():
            if self._has_field(k):
                filters[k] = v
        return qs.filter(**filters) if filters else qs

    def _apply_tenant_filter(self, qs, tenant_id: str):
        return qs.filter(**{f"{self.tenant_field}_id": tenant_id})

    def _apply_search(self, qs):
        q = self.request.query_params.get("q")
        if not q:
            return qs
        # If no search_fields defined, try common ones
        fields = tuple(self.search_fields) or tuple(
            f for f in ("name", "title", "description") if self._has_field(f)
        )
        if not fields:
            return qs
        cond = Q()
        for f in fields:
            cond |= Q(**{f"{f}__icontains": q})
        return qs.filter(cond)

    def _apply_ordering(self, qs):
        order_param = self.request.query_params.get("order")
        fields_allowed = set(self.ordering_fields or ())
        if order_param:
            items = [s.strip() for s in order_param.split(",") if s.strip()]
            cleaned = []
            for it in items:
                base = it[1:] if it.startswith("-") else it
                if not fields_allowed or base in fields_allowed:
                    cleaned.append(it)
            if cleaned:
                return qs.order_by(*cleaned)
        # Default ordering if present
        return qs.order_by(*self.default_ordering) if self.default_ordering else qs

    def _apply_simple_filters(self, qs):
        """
        For any query param that matches a real model field (and is not control param),
        apply an exact filter. For 'in' semantics, allow CSV via <field>__in=a,b,c
        """
        IGNORE = {self.tenant_query_param, "q", "order", "page", "page_size"}
        params = self.request.query_params
        filters: Dict[str, Any] = {}

        for key, value in params.items():
            if key in IGNORE:
                continue

            # Support explicit Django lookup (e.g., price__gte)
            base = key.split("__", 1)[0]

            # Only apply if base exists on model
            if not self._has_field(base):
                continue

            if key.endswith("__in"):
                filters[key] = [v for v in value.split(",") if v != ""]
            else:
                filters[key] = value

        return qs.filter(**filters) if filters else qs

    def get_queryset(self):
        # Start from declared queryset / model default manager
        if hasattr(self, "queryset") and self.queryset is not None:
            qs = self.queryset.all()
        else:
            qs = self._model_class().objects.all()

        tenant_id = self.get_tenant_id()

        # No tenant provided
        if not tenant_id:
            if self.action == "list" and self.allow_public_list:
                qs = self._apply_public_filters(qs)
            else:
                # For safe methods, return empty; for mutations, block
                if self.request.method in SAFE_METHODS:
                    return qs.none()
                raise PermissionDenied("Missing tenant context")

        else:
            qs = self._apply_tenant_filter(qs, tenant_id)

        # Generic query features
        qs = self._apply_simple_filters(qs)
        qs = self._apply_search(qs)
        qs = self._apply_ordering(qs)
        return qs


# -----------------------------
# Public list mixin
# -----------------------------
class PublicListNoTenantMixin:
    """
    Mixin to allow GET / list without tenant (uses `public_filters`), while still
    requiring tenant for detail and all write operations.

    Use it together with TenantScopedModelViewSet:

        class ProductViewSet(PublicListNoTenantMixin, TenantScopedModelViewSet):
            allow_public_list = True
            public_filters = {"is_public": True, "is_active": True}
            search_fields = ("name", "description")
            ordering_fields = ("created_at", "name", "default_price")
    """
    allow_public_list = True



# # common/mixins.py
# from rest_framework.permissions import BasePermission, SAFE_METHODS
# from rest_framework import viewsets
# from rest_framework.exceptions import PermissionDenied
# from django.db.models import QuerySet

# TENANT_HEADER = "HTTP_X_TENANT_ID"  # maps to X-Tenant-ID

class PublicReadTenantOptional(BasePermission):
    """GET/HEAD/OPTIONS: public; other methods require JWT + X-Tenant-ID."""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        # write ops must be authenticated and carry tenant
        return bool(request.user and request.user.is_authenticated and request.META.get(TENANT_HEADER))

class PrivateTenantOnly(BasePermission):
    """All methods require JWT + X-Tenant-ID."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.META.get(TENANT_HEADER))

# ... existing imports ...
from platformapp.services.audit import log_event

class AuditedActionsMixin:
    """Attach to ViewSets you want to auto-audit."""
    def _audit(self, action: str, obj, meta=None):
        tenant = getattr(obj, "tenant", None) or self.get_tenant(self.request)  # from your TenantScopedModelViewSet
        user_id = getattr(self.request.user, "id", None)
        entity = obj.__class__.__name__
        entity_id = getattr(obj, "id", None) or ""
        try:
            log_event(tenant=tenant, user_id=str(user_id) if user_id else None,
                      action=action, entity=entity, entity_id=str(entity_id), meta=meta or {})
        except Exception:
            # Never break the request on audit failure
            pass

    def perform_create(self, serializer):
        obj = serializer.save()
        self._audit("create", obj, meta={"path": self.request.path, "method": self.request.method})
        return obj

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit("update", obj, meta={"path": self.request.path, "method": self.request.method})
        return obj

    def perform_destroy(self, instance):
        self._audit("delete", instance, meta={"path": self.request.path, "method": self.request.method})
        return super().perform_destroy(instance)

# class TenantScopedModelViewSet(viewsets.ModelViewSet):
#     """
#     Automatic filtering by X-Tenant-ID (if provided or required by permission).
#     For public read, it will not filter on tenant unless explicitly coded
#     in your queryset (e.g., public availability constraints).
#     """
#     tenant_lookup_field = "tenant_id"  # models must have tenant FK field named 'tenant'

#     def get_tenant_id(self):
#         return self.request.META.get(TENANT_HEADER)

#     def get_queryset(self) -> QuerySet:
#         qs = super().get_queryset()
#         # If PrivateTenantOnly is in use OR a tenant header is present, enforce scoping
#         tenant_id = self.get_tenant_id()
#         is_private = any(isinstance(p(), PrivateTenantOnly) for p in getattr(self, "permission_classes", []))
#         if tenant_id or is_private:
#             if not tenant_id:
#                 raise PermissionDenied("X-Tenant-ID header required.")
#             qs = qs.filter(**{self.tenant_lookup_field: tenant_id})
#         return qs


# # # common/mixins.py
# # from typing import Optional
# # from django.db.models import QuerySet
# # from django.utils.functional import cached_property
# # from rest_framework.viewsets import ModelViewSet
# # from rest_framework.permissions import SAFE_METHODS
# # from rest_framework.exceptions import PermissionDenied
# # from platformapp.models import Tenant

# # class TenantScopedModelViewSet(ModelViewSet):
# #     """
# #     Unified multi-tenant behavior:
# #       - Resolves tenant from header 'X-Tenant-ID', query '?tenant=', or (optionally) request.user.tenant
# #       - If tenant is resolved => filter queryset by tenant
# #       - If NO tenant:
# #           * SAFE methods (GET/HEAD/OPTIONS) => return a 'public queryset' (overrideable per view)
# #           * write methods => deny (require tenant context)
# #       - On writes, tenant is injected server-side; payload tenant is ignored.
# #     """
# #     tenant_header = "X-Tenant-ID"
# #     tenant_query_param = "tenant"

# #     def _resolve_tenant_id(self) -> Optional[str]:
# #         req = self.request
# #         tid = req.headers.get(self.tenant_header) or req.query_params.get(self.tenant_query_param)
# #         if not tid and getattr(req.user, "is_authenticated", False):
# #             # Optional: If your user model has a single-tenant relation:
# #             tenant = getattr(req.user, "tenant", None)
# #             if tenant:
# #                 tid = str(getattr(tenant, "id", "") or "")
# #         return tid or None

# #     @cached_property
# #     def current_tenant(self) -> Optional[Tenant]:
# #         tid = self._resolve_tenant_id()
# #         if not tid:
# #             return None
# #         try:
# #             return Tenant.objects.get(id=tid)
# #         except Tenant.DoesNotExist:
# #             return None

# #     def public_queryset(self, qs: QuerySet) -> QuerySet:
# #         """
# #         Default public scope: if model has `is_active`, show active.
# #         Override in individual ViewSets for richer rules (`is_public`, `published_at`, etc).
# #         """
# #         if hasattr(qs.model, "is_active"):
# #             qs = qs.filter(is_active=True)
# #         return qs

# #     def get_queryset(self):
# #         qs = super().get_queryset()
# #         tenant = self.current_tenant
# #         if tenant:
# #             # Models that are tenant-scoped must have a tenant FK named 'tenant'
# #             return qs.filter(tenant=tenant)
# #         # No tenant on SAFE => public read; on write => none (denied later)
# #         if self.request.method in SAFE_METHODS:
# #             return self.public_queryset(qs)
# #         return qs.none()

# #     def initial(self, request, *args, **kwargs):
# #         """
# #         Enforce auth+tenant for write operations (POST/PUT/PATCH/DELETE).
# #         """
# #         super().initial(request, *args, **kwargs)
# #         if request.method not in SAFE_METHODS:
# #             if not request.user or not request.user.is_authenticated:
# #                 raise PermissionDenied("Authentication required.")
# #             if not self.current_tenant:
# #                 raise PermissionDenied("Tenant context required (send X-Tenant-ID or ?tenant=).")

# #     def perform_create(self, serializer):
# #         tenant = self.current_tenant
# #         if not tenant:
# #             raise PermissionDenied("Tenant context required for create.")
# #         serializer.save(tenant=tenant)

# #     def perform_update(self, serializer):
# #         tenant = self.current_tenant
# #         if not tenant:
# #             raise PermissionDenied("Tenant context required for update.")
# #         # Ensure tenant cannot be changed through payload
# #         serializer.save(tenant=tenant)
