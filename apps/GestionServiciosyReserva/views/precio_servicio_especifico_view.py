from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission

from ..serializers.precioservicio_serializer import PrecioServicioSerializer
from ..services.precio_servicio_especifico_service import PrecioServicioEspecificoService


class PrecioServicioEspecificoView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]

    # Puedes dejar SERV_CITAS para no crear otro permiso todavía.
    # Si ya tienes un componente específico de precios, puedes cambiarlo.
    rbac_component = "SERV_CITAS"

    @extend_schema(
        tags=["Precios Servicio"],
        operation_id="gestion_servicios_precio_servicio_especifico",
        parameters=[
            OpenApiParameter(
                name="modalidad",
                type=str,
                required=False,
                description="Modalidad del precio: CLINICA o DOMICILIO.",
            ),
        ],
        responses={
            200: PrecioServicioSerializer(many=True),
            404: OpenApiResponse(description="No se encontraron precios activos."),
        },
    )
    def get(self, request, id_servicio):
        modalidad = request.query_params.get("modalidad")

        precios = PrecioServicioEspecificoService.listar_por_servicio(
            veterinaria_id=self.get_tenant_id(),
            servicio_id=id_servicio,
            modalidad=modalidad,
        )

        serializer = PrecioServicioSerializer(precios, many=True)

        if not precios.exists():
            return Response(
                {
                    "ok": False,
                    "id_servicio": id_servicio,
                    "modalidad": modalidad,
                    "total": 0,
                    "precios": [],
                    "mensaje": "No se encontraron precios activos para el servicio y modalidad indicados.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "ok": True,
                "id_servicio": id_servicio,
                "modalidad": str(modalidad).upper() if modalidad else None,
                "total": precios.count(),
                "precios": serializer.data,
            },
            status=status.HTTP_200_OK,
        )