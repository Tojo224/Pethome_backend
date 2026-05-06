from django.db.models import Q
from ..models.grupo_permiso_componente import GrupoPermisoComponente
from ..models.componente_sistema import ComponenteSistema

class ComponenteSelector:
    @staticmethod
    def get_componentes_permitidos(user, plataforma="WEB"):
        """
        Obtiene los componentes permitidos para un usuario en una plataforma específica.
        Realiza la unión (OR lógico) de permisos si el usuario pertenece a varios grupos.
        """
        if user.is_superuser:
            return ComponenteSistema.objects.filter(
                estado=True,
                plataforma__in=[plataforma, "AMBOS"]
            ).order_by("orden")

        # Obtener todos los permisos activos del usuario en sus grupos activos de su veterinaria
        permisos_queryset = GrupoPermisoComponente.objects.filter(
            estado=True,
            id_grupo__estado=True,
            id_grupo__id_veterinaria=user.id_veterinaria,
            id_grupo__usuario_grupo__id_usuario=user,
            id_grupo__usuario_grupo__estado=True,
            id_componente__estado=True,
            id_componente__plataforma__in=[plataforma, "AMBOS"],
            puede_ver=True
        ).select_related("id_componente")

        # Procesar permisos combinando grupos (Refinamiento: OR lógico)
        componentes_permitidos = {}
        
        for p in permisos_queryset:
            comp_id = p.id_componente_id
            if comp_id not in componentes_permitidos:
                componentes_permitidos[comp_id] = {
                    "id_componente": p.id_componente.id_componente,
                    "codigo": p.id_componente.codigo,
                    "nombre": p.id_componente.nombre,
                    "tipo": p.id_componente.tipo,
                    "modulo": p.id_componente.modulo,
                    "ruta": p.id_componente.ruta,
                    "plataforma": p.id_componente.plataforma,
                    "id_padre": p.id_componente.id_padre_id,
                    "orden": p.id_componente.orden,
                    "permisos": {
                        "ver": False,
                        "crear": False,
                        "editar": False,
                        "eliminar": False,
                        "exportar": False,
                        "ejecutar": False,
                    },
                    "_obj": p.id_componente # Guardamos referencia para la recursión posterior
                }
            
            # Aplicar OR lógico
            permisos = componentes_permitidos[comp_id]["permisos"]
            permisos["ver"] = permisos["ver"] or p.puede_ver
            permisos["crear"] = permisos["crear"] or p.puede_crear
            permisos["editar"] = permisos["editar"] or p.puede_editar
            permisos["eliminar"] = permisos["eliminar"] or p.puede_eliminar
            permisos["exportar"] = permisos["exportar"] or p.puede_exportar
            permisos["ejecutar"] = permisos["ejecutar"] or p.puede_ejecutar

        return list(componentes_permitidos.values())

    @staticmethod
    def get_veterinaria_context(user):
        """Retorna el objeto veterinaria si existe y está activa."""
        if user.is_superuser:
            return None
            
        veterinaria = getattr(user, "id_veterinaria", None)
        if veterinaria and veterinaria.estado:
            return veterinaria
        return None
