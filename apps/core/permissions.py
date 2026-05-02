"""Custom DRF permission classes."""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasRole(BasePermission):
    """Generator: `HasRole.with_roles('SUPER_ADMIN','ADMIN')` — tegishli rollarga ruxsat."""

    allowed_roles: tuple[str, ...] = ()

    @classmethod
    def with_roles(cls, *roles):
        return type(f'HasRole_{"_".join(roles)}', (cls,), {'allowed_roles': roles})

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if not self.allowed_roles:
            return True
        role = getattr(user, 'role', None)
        return bool(role and role.name in self.allowed_roles)


class IsAdminRole(BasePermission):
    """`SUPER_ADMIN` yoki `ADMIN` roli."""

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        role = getattr(user, 'role', None)
        return bool(role and role.name in ('SUPER_ADMIN', 'ADMIN'))


class IsOwnerOrReadOnly(BasePermission):
    """SAFE methods barchaga, write esa faqat `created_by == user`."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, 'created_by_id', None)
        return owner == request.user.id
