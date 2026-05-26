from rest_framework.permissions import BasePermission

from ..models import GrupoPermisoComponente, UsuarioGrupo


class HasComponentPermission(BasePermission):
    message = "No tienes permisos para realizar esta accion."

    method_action_map = {
        "GET": "puede_ver",
        "HEAD": "puede_ver",
        "OPTIONS": "puede_ver",
        "POST": "puede_crear",
        "PUT": "puede_editar",
        "PATCH": "puede_editar",
        "DELETE": "puede_eliminar",
    }
    client_component_fallback = {
        "CLI_CLIENTES",
        "CLI_MASCOTAS",
        "CLI_CATALOGOS",
        "CLI_HISTORIALES",
        "SERV_CITAS",
        "SERV_SERVICIOS",
        "SERV_PRECIOS",
        "MOVIL_MI_PERFIL",
    }
    admin_write_fallback_components = {
        "INV_PRODUCTOS",
    }

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True

        component = getattr(view, "rbac_component", None)
        if not component:
            return False

        action_field = self.method_action_map.get(request.method)
        if not action_field:
            return False

        tenant = getattr(request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        if not tenant_id:
            tenant_id = getattr(user, "veterinaria_id", None)
        if not tenant_id:
            return False

        grupos_ids = list(
            UsuarioGrupo.objects.filter(
                usuario=user,
                estado=True,
                grupo__estado=True,
                grupo__veterinaria_id=tenant_id,
            ).values_list("grupo_id", flat=True)
        )

        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        # Fallback inmediato para ADMIN del tenant actual, incluso cuando
        # todavía no terminó el seed de grupos/permisos base.
        if not grupos_ids and role_name == "ADMIN" and getattr(user, "veterinaria_id", None) == tenant_id:
            return True
        if not grupos_ids:
            return False

        perms = GrupoPermisoComponente.objects.filter(
            grupo_id__in=grupos_ids,
            componente__codigo=component,
            estado=True,
            grupo__estado=True,
            componente__estado=True,
        )

        has_perm = perms.filter(**{action_field: True}).exists()

        # Fallback seguro para CLIENT en mÃ³vil:
        # permite operar componentes cliente aun si el seed base del tenant no se ejecutÃ³.
        if not has_perm:
            if (
                role_name == "ADMIN"
                and getattr(user, "veterinaria_id", None) == tenant_id
            ):
                return True
            if (
                role_name == "CLIENT"
                and component in self.client_component_fallback
                and getattr(user, "veterinaria_id", None) == tenant_id
            ):
                return True
            # Compatibilidad para componentes legacy de inventario:
            # si un ADMIN tiene permiso de ver el componente en su tenant,
            # se permite escritura para no bloquear flujos existentes.
            if (
                role_name == "ADMIN"
                and component in self.admin_write_fallback_components
                and getattr(user, "veterinaria_id", None) == tenant_id
                and perms.filter(puede_ver=True).exists()
            ):
                return True

        if not has_perm:
            from ..services.bitacora_register_service import BitacoraService
            from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
            
            BitacoraService.registrar_evento(
                accion=BitacoraAccion.ACCESO_DENEGADO,
                descripcion=f"Intento de acceso no autorizado al componente '{component}' ({request.method}).",
                usuario=user,
                request=request,
                modulo=BitacoraModulo.SISTEMA,
                resultado=BitacoraResultado.FALLO,
                metadatos={
                    "componente": component,
                    "metodo": request.method,
                    "path": request.path
                }
            )

        return has_perm
