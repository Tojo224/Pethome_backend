from rest_framework.permissions import BasePermission

from apps.AutenticacionySeguridad.enums.roles import RoleEnum


class IsAdminOrVeterinarianForSales(BasePermission):
    message = "No tienes permisos para registrar o consultar ventas presenciales."

    allowed_roles = {
        RoleEnum.ADMIN.value,
        RoleEnum.VETERINARIAN.value,
    }

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True

        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        return role_name in self.allowed_roles
