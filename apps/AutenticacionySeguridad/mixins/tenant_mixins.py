from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService

class TenantViewMixin:
    """
    Mixin para centralizar la lógica de identificación de Tenant 
    y registro seguro de bitácora en todas las vistas.
    """
    
    def get_tenant_id(self):
        """Resuelve el ID de la veterinaria actual."""
        tenant = getattr(self.request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        if tenant_id:
            return tenant_id
        return getattr(self.request.user, "veterinaria_id", None)

    def registrar_bitacora(self, **kwargs):
        """Envuelve la llamada a BitacoraService de forma segura."""
        try:
            # Si no se pasa el usuario explícitamente, intentar tomarlo del request
            if "usuario" not in kwargs and hasattr(self, "request"):
                kwargs["usuario"] = self.request.user
            
            # Si no se pasa el request, intentar tomarlo de la instancia
            if "request" not in kwargs and hasattr(self, "request"):
                kwargs["request"] = self.request
                
            BitacoraService.registrar_evento(**kwargs)
        except Exception:
            # Fallo silencioso para no interrumpir el flujo principal
            pass
