from rest_framework.permissions import BasePermission, SAFE_METHODS

class RolePermission(BasePermission):
    message = "ليست لديك الصلاحية اللازمة."
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser or user.role == "ADMIN":
            return True
        if request.method in SAFE_METHODS:
            return True
        return user.role in getattr(view, "write_roles", set())
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)

class AdminOnlyPermission(BasePermission):
    message = "هذه العملية متاحة لمدير النظام فقط."
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and (u.is_superuser or u.role == "ADMIN"))
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
