from rest_framework.permissions import BasePermission


class IsDriver(BasePermission):
    message = 'Only drivers can access this endpoint'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return user.groups.filter(name='Driver').exists()


class IsRider(BasePermission):
    message = 'Only riders can access this endpoint'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return user.groups.filter(name='Rider').exists()
