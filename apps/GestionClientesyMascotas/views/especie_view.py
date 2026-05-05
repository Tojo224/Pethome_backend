from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService
from apps.GestionClientesyMascotas.models.especie import Especie
from apps.GestionClientesyMascotas.serializers.especie_serializer import EspecieSerializer


def _registrar_bitacora_seguro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        pass


class EspecieListView(generics.ListAPIView):
    queryset = Especie.objects.all().order_by("nombre")
    serializer_class = EspecieSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CATALOGOS"

    @extend_schema(tags=["Catalogos"], responses={200: EspecieSerializer})
    def get(self, request, *args, **kwargs):
        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.VISUALIZAR,
            descripcion="Consulta de catálogo de especies.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.CATALOGOS,
            entidad_tipo="Especie",
            resultado=BitacoraResultado.EXITO,
        )
        return super().get(request, *args, **kwargs)