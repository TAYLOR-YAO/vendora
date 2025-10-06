try:
    from django_filters.rest_framework import DjangoFilterBackend
    HAS_DF = True
except Exception:
    HAS_DF = False

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

from common.mixins import TenantScopedModelViewSet, PrivateTenantOnly
from .models import Tenant, Role, UserRole, AuditLog
from .serializers import TenantSerializer, RoleSerializer, UserRoleSerializer, AuditLogSerializer

def _apply_common(qs, request, search_fields=None):
    from commerce.views import _apply_common_query_params
    return _apply_common_query_params(qs, request, search_fields=search_fields)

# Public utility: resolve tenant id by slug (useful for UI bootstrapping by domain/slug)
class TenantResolveView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        slug = (request.query_params.get("slug") or "").strip()
        if not slug:
            return Response({"detail": "slug required"}, status=400)
        try:
            t = Tenant.objects.get(slug=slug, status__in=["active"])
            return Response({"id": str(t.id), "slug": t.slug, "name": t.name, "plan": t.plan, "region": t.region})
        except Tenant.DoesNotExist:
            return Response({"detail": "not found"}, status=404)


class TenantViewSet(TenantScopedModelViewSet):
    queryset = Tenant.objects.all().order_by("name")
    serializer_class = TenantSerializer
    permission_classes = [PrivateTenantOnly]  # manage tenants privately
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = ["slug", "status", "plan", "region"]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["name", "slug"])


class RoleViewSet(TenantScopedModelViewSet):
    queryset = Role.objects.all().order_by("name")
    serializer_class = RoleSerializer
    permission_classes = [PrivateTenantOnly]
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = ["name", "scope_level"]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["name", "scope_level"])

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.META.get("HTTP_X_TENANT_ID"))


class UserRoleViewSet(TenantScopedModelViewSet):
    queryset = UserRole.objects.select_related("role").order_by("-created_at")
    serializer_class = UserRoleSerializer
    permission_classes = [PrivateTenantOnly]
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = ["role", "user_id", "business_id", "store_id"]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["user_id"])

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.META.get("HTTP_X_TENANT_ID"))


class AuditLogViewSet(TenantScopedModelViewSet):
    queryset = AuditLog.objects.select_related("tenant").order_by("-created_at")
    serializer_class = AuditLogSerializer
    permission_classes = [PrivateTenantOnly]
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = ["action", "entity", "entity_id", "user_id"]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["action", "entity", "entity_id", "user_id"])

# class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = AuditLog.objects.all().order_by("-created_at")
#     serializer_class = AuditLogSerializer
#     permission_classes = [IsAdminUser]
#     filterset_fields = {"tenant": ["exact"], "user_id": ["exact"], "action": ["icontains"], "entity": ["icontains"]}
#     search_fields = ["entity", "entity_id", "action"]