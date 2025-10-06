from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantViewSet, RoleViewSet, UserRoleViewSet, AuditLogViewSet,
    TenantResolveView,   # <-- add
)

router = DefaultRouter()
router.register(r'tenant', TenantViewSet)
router.register(r'role', RoleViewSet)
router.register(r'userrole', UserRoleViewSet)
router.register(r'auditlog', AuditLogViewSet)

urlpatterns = [
    path('tenant/resolve/', TenantResolveView.as_view(), name='tenant-resolve'),  # <-- public GET ?slug=
    path('', include(router.urls)),
    
]
