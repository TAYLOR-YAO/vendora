# backend/crm/permissions.py
from common.permissions import PrivateTenantOnly, IsAdminOrReadOnly, IsOwnerOrAdmin
__all__ = ["PrivateTenantOnly", "IsAdminOrReadOnly", "IsOwnerOrAdmin"]
