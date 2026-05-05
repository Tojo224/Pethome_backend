from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema

from ..filters import BitacoraFilter
from ..models.bitacora import Bitacora
from ..permissions.tenant_rbac import HasComponentPermission
from ..serializers.bitacora_serializer import BitacoraSerializer
from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from ..mixins.tenant_mixins import TenantViewMixin
from ..selectors.bitacora_selector import BitacoraSelector





class BitacoraPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class BitacoraListView(TenantViewMixin, generics.ListAPIView):
    serializer_class = BitacoraSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_BITACORA"
    pagination_class = BitacoraPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = BitacoraFilter
    ordering_fields = ["fecha_hora", "id_bitacora"]
    ordering = ["-fecha_hora"]

    @extend_schema(
        tags=["Bitacora"],
        parameters=[
            OpenApiParameter("fecha_desde", OpenApiTypes.DATETIME, required=False),
            OpenApiParameter("fecha_hasta", OpenApiTypes.DATETIME, required=False),
            OpenApiParameter("es_global", OpenApiTypes.BOOL, required=False),
            OpenApiParameter("ordering", OpenApiTypes.STR, required=False),
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False),
        ],
        responses={200: BitacoraSerializer},
    )
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.registrar_bitacora(
            accion="BITACORA_CONSULTADA",
            descripcion="Consulta al listado de bitácora del sistema.",
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "filtros": request.query_params.dict()
            }
        )
        return response

    def get_queryset(self):
        return BitacoraSelector.get_visible_bitacora(
            user=self.request.user,
            veterinaria_id=self.get_tenant_id()
        )


class BitacoraDetailView(TenantViewMixin, generics.RetrieveAPIView):
    serializer_class = BitacoraSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_BITACORA"
    lookup_field = "pk"

    @extend_schema(
        tags=["Bitacora"],
        responses={200: BitacoraSerializer},
    )
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if response.status_code == 200:
            self.registrar_bitacora(
                accion="BITACORA_DETALLE_CONSULTADO",
                descripcion="Consulta al detalle de un evento de bitácora.",
                modulo=BitacoraModulo.AUTENTICACION,
                entidad_tipo="Bitacora",
                entidad_id=kwargs.get("pk"),
                resultado=BitacoraResultado.EXITO
            )
        return response

    def get_queryset(self):
        return BitacoraSelector.get_visible_bitacora(
            user=self.request.user,
            veterinaria_id=self.get_tenant_id()
        )
