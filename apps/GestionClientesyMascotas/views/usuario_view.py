from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService
from apps.AutenticacionySeguridad.models.user import User


def _registrar_bitacora_seguro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        pass


class UsuarioListSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id_usuario", "nombre"]

    def get_nombre(self, obj) -> str:
        try:
            return obj.perfil.nombre
        except Exception:
            return f"Usuario {obj.id_usuario}"


class UsuarioListView(generics.ListAPIView):
    serializer_class = UsuarioListSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CLIENTES"

    @extend_schema(tags=["Clientes"], responses={200: UsuarioListSerializer})
    def get(self, request, *args, **kwargs):
        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.USUARIO_CONSULTADO,
            descripcion="Consulta de usuarios activos para selector.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="User",
            resultado=BitacoraResultado.EXITO,
        )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        return User.objects.filter(
            role_id=3,
            is_active=True,
            veterinaria_id=tenant_id,
        ).order_by("id_usuario")