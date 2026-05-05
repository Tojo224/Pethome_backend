from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService
from apps.GestionClientesyMascotas.models.raza import Raza
from apps.GestionClientesyMascotas.serializers.raza_serializer import RazaSerializer


def _registrar_bitacora_seguro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        pass


class RazaListView(generics.ListAPIView):
    serializer_class = RazaSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CATALOGOS"

    @extend_schema(
        tags=["Catalogos"],
        parameters=[
            OpenApiParameter("especie_id", OpenApiTypes.INT, required=False),
        ],
        responses={200: RazaSerializer},
    )
    def get(self, request, *args, **kwargs):
        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.VISUALIZAR,
            descripcion="Consulta de catálogo de razas.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.CATALOGOS,
            entidad_tipo="Raza",
            resultado=BitacoraResultado.EXITO,
            metadatos={"especie_id": request.query_params.get("especie_id")},
        )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Raza.objects.select_related("especie").all().order_by("nombre")
        especie_id = self.request.query_params.get("especie_id")

        if especie_id:
            queryset = queryset.filter(especie_id=especie_id)

        return queryset