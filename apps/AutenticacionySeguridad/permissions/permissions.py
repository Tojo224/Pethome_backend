from rest_framework.permissions import BasePermission
from apps.AutenticacionySeguridad.enums.roles import RoleEnum

from ..events.bitacora_events import BitacoraModulo
from ..services.bitacora_register_service import BitacoraService


def _resolver_modulo_desde_request(request):
    path = (getattr(request, "path", "") or "").lower()

    if "/api/auth/bitacora" in path:
        return BitacoraModulo.BITACORA
    if "/api/auth/" in path:
        return BitacoraModulo.AUTENTICACION

    if "/api/gestion/clientes/mascotas" in path:
        return BitacoraModulo.MASCOTAS
    if "/api/gestion/clientes/especies" in path or "/api/gestion/clientes/razas" in path:
        return BitacoraModulo.CATALOGOS
    if "/api/gestion/clientes/" in path:
        return BitacoraModulo.CLIENTES

    if "/api/gestion/servicios/citas" in path:
        return BitacoraModulo.CITAS
    if "/api/gestion/servicios/precios" in path:
        return BitacoraModulo.PRECIOS
    if "/api/gestion/servicios/categorias" in path:
        return BitacoraModulo.CATALOGOS
    if "/api/gestion/servicios/" in path:
        return BitacoraModulo.SERVICIOS

    return BitacoraModulo.SISTEMA


def _registrar_acceso_denegado_seguro(request, mensaje, allowed_roles):
    try:
        usuario = request.user if getattr(request.user, "is_authenticated", False) else None
        rol = getattr(getattr(request, "user", None), "role", None)
        nombre_rol = getattr(rol, "nombre", None)

        BitacoraService.registrar_acceso_denegado(
            request=request,
            descripcion=mensaje,
            usuario=usuario,
            modulo=_resolver_modulo_desde_request(request),
            metadatos={
                "metodo": getattr(request, "method", ""),
                "path": getattr(request, "path", ""),
                "rol_actual": nombre_rol,
                "roles_permitidos": allowed_roles,
            },
        )
    except Exception:
        pass


class HasRolePermission(BasePermission):
    allowed_roles = []
    message = "No tienes permisos para realizar esta acción."

    def has_permission(self, request, view):
        user = request.user
        permitido = (
            user
            and user.is_authenticated
            and getattr(user, "role", None)
            and user.role.nombre in self.allowed_roles
        )

        if not permitido:
            _registrar_acceso_denegado_seguro(request, self.message, self.allowed_roles)

        return permitido


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

class IsClientAdminOrVeterinario(HasRolePermission):
    allowed_roles = [
        RoleEnum.ADMIN.value,
        RoleEnum.VETERINARIAN.value,
        RoleEnum.CLIENT.value,
    ]
    message = "Solo administradores, veterinarios o clientes pueden realizar esta acción."
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