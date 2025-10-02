from rest_framework import viewsets
from .models import Tenant, Role, UserRole
from .serializers import TenantSerializer, RoleSerializer, UserRoleSerializer

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all().order_by('-id') if hasattr(Tenant, 'id') else Tenant.objects.all()
    serializer_class = TenantSerializer

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().order_by('-id') if hasattr(Role, 'id') else Role.objects.all()
    serializer_class = RoleSerializer

class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRole.objects.all().order_by('-id') if hasattr(UserRole, 'id') else UserRole.objects.all()
    serializer_class = UserRoleSerializer
