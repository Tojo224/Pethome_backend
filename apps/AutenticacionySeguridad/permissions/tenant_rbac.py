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
    client_read_only_fallback = {
        "CLI_PLAN_SANITARIO",
    }
    veterinarian_component_fallback = {
        "CLI_PLAN_SANITARIO",
    }
    admin_write_fallback_components = {
        "INV_PRODUCTOS",
    }

    def _has_role_fallback(self, *, role_name, component, action_field, tenant_id, user, perms):
        if (
            role_name == "ADMIN"
            and getattr(user, "veterinaria_id", None) == tenant_id
        ):
            return True
        if (
            role_name == "CLIENT"
            and component in self.client_read_only_fallback
            and action_field == "puede_ver"
            and getattr(user, "veterinaria_id", None) == tenant_id
        ):
            return True
        if (
            role_name == "CLIENT"
            and component in self.client_component_fallback
            and getattr(user, "veterinaria_id", None) == tenant_id
        ):
            return True
        if (
            role_name == "VETERINARIAN"
            and component in self.veterinarian_component_fallback
            and getattr(user, "veterinaria_id", None) == tenant_id
        ):
            return True
        if (
            role_name == "ADMIN"
            and component in self.admin_write_fallback_components
            and getattr(user, "veterinaria_id", None) == tenant_id
            and perms.filter(puede_ver=True).exists()
        ):
            return True
        return False

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

        if not grupos_ids:
            return self._has_role_fallback(
                role_name=role_name,
                component=component,
                action_field=action_field,
                tenant_id=tenant_id,
                user=user,
                perms=GrupoPermisoComponente.objects.none(),
            )

        perms = GrupoPermisoComponente.objects.filter(
            grupo_id__in=grupos_ids,
            componente__codigo=component,
            estado=True,
            grupo__estado=True,
            componente__estado=True,
        )

        has_perm = perms.filter(**{action_field: True}).exists()

        if not has_perm and self._has_role_fallback(
            role_name=role_name,
            component=component,
            action_field=action_field,
            tenant_id=tenant_id,
            user=user,
            perms=perms,
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
                    "path": request.path,
                },
            )

        return has_perm
