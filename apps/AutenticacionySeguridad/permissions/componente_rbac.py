from rest_framework.permissions import BasePermission
from ..selectors.componente_selector import ComponenteSelector

class TienePermisoComponente(BasePermission):
    """
    Permiso personalizado que valida si el usuario tiene permiso sobre un componente específico.
    Se espera que la vista defina 'codigo_componente' y opcionalmente 'accion_permiso'.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        codigo = getattr(view, "codigo_componente", None)
        accion = getattr(view, "accion_permiso", "ver")
        plataforma = getattr(view, "plataforma_permiso", "WEB")

        if not codigo:
            return True # Si la vista no define componente, se asume que no requiere esta validación

        # Obtener componentes permitidos del usuario
        componentes = ComponenteSelector.get_componentes_permitidos(request.user, plataforma)
        
        # Buscar el componente y validar la acción
        for comp in componentes:
            if comp["codigo"] == codigo:
                return comp["permisos"].get(accion, False)

        return False
