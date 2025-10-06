from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOperatorOrReadOnly(BasePermission):
    """
    Read for everyone *in the tenant scope*; write only for staff/operators.
    You can refine by checking your platform roles if needed.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        u = request.user
        return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))
