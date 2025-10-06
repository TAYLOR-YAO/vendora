# backend/business/permissions.py
from common.permissions import ReadPublicWriteAuth, IsAdminOrReadOnly, IsOwnerOrAdmin
__all__ = ["ReadPublicWriteAuth", "IsAdminOrReadOnly", "IsOwnerOrAdmin"]
