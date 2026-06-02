from rest_framework.permissions import BasePermission
from apps.AutenticacionySeguridad.enums.roles import RoleEnum


class IsReporteRole(BasePermission):
    """Permite el acceso solo a SUPERADMIN, ADMIN y VETERINARIAN."""

    allowed = {"SUPERADMIN", RoleEnum.ADMIN.value, RoleEnum.VETERINARIAN.value}
    message = "No tienes permisos para acceder a reportes."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        role_name = (getattr(getattr(user, "role", None), "nombre", None) or "").upper()
        return role_name in self.allowed
