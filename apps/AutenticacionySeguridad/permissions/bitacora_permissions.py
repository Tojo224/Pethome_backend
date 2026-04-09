from rest_framework import permissions
from ..enums.roles import RoleEnum
from ..models.bitacora import Bitacora

class PuedeVerBitacora(permissions.BasePermission):
    message = "No tienes permisos para consultar la bitácora."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        role = getattr(user, "role", None)
        if role and role.nombre == RoleEnum.ADMIN.value:
            return True

        permiso_lectura = f"{Bitacora._meta.app_label}.view_{Bitacora._meta.model_name}"
        return bool(
            user.has_perm(permiso_lectura)
        )