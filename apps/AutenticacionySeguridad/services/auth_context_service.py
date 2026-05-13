from ..selectors.componente_selector import ComponenteSelector
from ..services.componente_tree_service import ComponenteTreeService
from ..models.suscripcion import Suscripcion

class PlanSelector:
    @staticmethod
    def get_active_plan(veterinaria):
        if not veterinaria:
            return None
        
        suscripcion = Suscripcion.objects.filter(
            veterinaria=veterinaria,
            estado_suscripcion__in=["ACTIVA", "PRUEBA"]
        ).select_related("plan").order_by("-fecha_creacion").first()
        
        return suscripcion.plan if suscripcion else None

class AuthContextService:
    @staticmethod
    def get_auth_context(user, plataforma="WEB"):
        """
        Construye el JSON completo con el contexto del usuario, tenant y permisos.
        """
        plataforma = str(plataforma or "WEB").upper()
        veterinaria = ComponenteSelector.get_veterinaria_context(user)

        plan = PlanSelector.get_active_plan(veterinaria)
        
        # Obtener componentes y construir árbol
        componentes_planos = ComponenteSelector.get_componentes_permitidos(user, plataforma)
        componentes_arbol = ComponenteTreeService.build_context_tree(componentes_planos)
        
        contexto = {
            "usuario": {
                "id_usuario": user.id_usuario,
                "correo": user.correo,
                "rol": user.role.nombre if user.role_id else "Sin Rol",
                "id_veterinaria": user.veterinaria_id,
                "is_superuser": user.is_superuser,
            },
            "veterinaria": {
                "id_veterinaria": veterinaria.id_veterinaria,
                "nombre": veterinaria.nombre,
                "slug": veterinaria.slug,
                "logo": veterinaria.logo if veterinaria.logo else None,
                "estado": veterinaria.estado,
            } if veterinaria else None,
            "plan": {
                "nombre": plan.nombre,
                "limite_usuarios": plan.limite_usuarios,
                "limite_mascotas": plan.limite_mascotas,
                "permite_app_movil": plan.permite_app_movil,
                "permite_reportes": plan.permite_reportes,
                "permite_backup": plan.permite_backup,
            } if plan else None,
            "componentes": componentes_arbol,
        }
        
        return contexto
