from rest_framework.permissions import BasePermission
from apps.AutenticacionySeguridad.enums.roles import RoleEnum


class HasRolePermission(BasePermission):
    allowed_roles = []
    message = "No tienes permisos para realizar esta acción."

    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and getattr(user, "role", None)
            and user.role.nombre in self.allowed_roles
        )


class IsAdminRole(HasRolePermission):
    allowed_roles = [RoleEnum.ADMIN.value]
    message = "Solo los administradores pueden realizar esta acción."


class IsVeterinarianRole(HasRolePermission):
    allowed_roles = [RoleEnum.VETERINARIAN.value]
    message = "Solo los veterinarios pueden realizar esta acción."


class IsClientRole(HasRolePermission):
    allowed_roles = [RoleEnum.CLIENT.value]
    message = "Solo los clientes pueden realizar esta acción."


class IsAdminOrVeterinarian(HasRolePermission):
    allowed_roles = [
        RoleEnum.ADMIN.value,
        RoleEnum.VETERINARIAN.value,
    ]
    message = "Solo administradores o veterinarios pueden realizar esta acción."


class IsAdminOrClient(HasRolePermission):
    allowed_roles = [
        RoleEnum.ADMIN.value,
        RoleEnum.CLIENT.value,
    ]
    message = "Solo administradores o clientes pueden realizar esta acción."

"""
EQUIPO AVISO IMPORTANTE ESTO PARA CADA APP
El permissions.py define las reglas de acceso a los endpoints.
Si el tiempo lo permite aqui ira los Permisos específicos de la API.

poder crear clases personalizadas de permisos y reglas de acceso por rol o contexto HTTP.
(no tomar atencion por el momento)
"""