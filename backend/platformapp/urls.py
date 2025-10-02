from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import TenantViewSet
from .views import RoleViewSet
from .views import UserRoleViewSet

router = DefaultRouter()
router.register(r'tenant', TenantViewSet)
router.register(r'role', RoleViewSet)
router.register(r'userrole', UserRoleViewSet)

urlpatterns = [ path('', include(router.urls)) ]