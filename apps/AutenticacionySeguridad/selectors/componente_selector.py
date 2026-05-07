from ..models.componente_sistema import ComponenteSistema
from ..models.grupo_permiso_componente import GrupoPermisoComponente


class ComponenteSelector:
    @staticmethod
    def get_componentes_permitidos(user, plataforma="WEB"):
        """
        Obtiene componentes permitidos para un usuario en plataforma dada.
        Combina permisos de varios grupos con OR logico.
        """
        plataforma = str(plataforma or "WEB").upper()

        if user.is_superuser:
            componentes = ComponenteSistema.objects.filter(
                estado=True, plataforma__in=[plataforma, "AMBOS"]
            ).exclude(
                codigo__startswith="CLI_"
            ).exclude(
                codigo__startswith="SERV_"
            ).exclude(
                codigo__startswith="INV_"
            ).order_by("orden")
            
            return [
                {
                    "id_componente": c.id_componente,
                    "codigo": c.codigo,
                    "nombre": c.nombre,
                    "tipo": c.tipo,
                    "modulo": c.modulo,
                    "ruta": c.ruta,
                    "plataforma": c.plataforma,
                    "id_padre": c.padre_id,
                    "orden": c.orden,
                    "permisos": {
                        "ver": True,
                        "crear": True,
                        "editar": True,
                        "eliminar": True,
                        "exportar": True,
                        "ejecutar": True,
                    },
                    "_obj": c,
                }
                for c in componentes
            ]

        permisos_queryset = (
            GrupoPermisoComponente.objects.filter(
                estado=True,
                grupo__estado=True,
                grupo__veterinaria_id=user.veterinaria_id,
                grupo__usuarios_asignados__usuario=user,
                grupo__usuarios_asignados__estado=True,
                componente__estado=True,
                componente__plataforma__in=[plataforma, "AMBOS"],
                puede_ver=True,
            )
            .select_related("componente")
            .distinct()
        )

        componentes_permitidos = {}
        for p in permisos_queryset:
            comp_id = p.componente_id
            if comp_id not in componentes_permitidos:
                componentes_permitidos[comp_id] = {
                    "id_componente": p.componente.id_componente,
                    "codigo": p.componente.codigo,
                    "nombre": p.componente.nombre,
                    "tipo": p.componente.tipo,
                    "modulo": p.componente.modulo,
                    "ruta": p.componente.ruta,
                    "plataforma": p.componente.plataforma,
                    "id_padre": p.componente.padre_id,
                    "orden": p.componente.orden,
                    "permisos": {
                        "ver": False,
                        "crear": False,
                        "editar": False,
                        "eliminar": False,
                        "exportar": False,
                        "ejecutar": False,
                    },
                    "_obj": p.componente,
                }

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
        if user.is_superuser:
            return None
        veterinaria = getattr(user, "veterinaria", None)
        if veterinaria and getattr(veterinaria, "estado", False):
            return veterinaria
        return None

