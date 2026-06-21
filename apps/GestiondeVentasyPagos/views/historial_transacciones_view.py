from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.GestiondeVentasyPagos.permissions import IsAdminOrVeterinarianForSales
from apps.GestiondeVentasyPagos.selectors.historial_transacciones_selector import (
    HistorialTransaccionesSelector,
)
from apps.GestiondeVentasyPagos.serializers.historial_transacciones_serializer import (
    HistorialTransaccionDetailSerializer,
    HistorialTransaccionListSerializer,
)


class HistorialTransaccionesPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class HistorialTransaccionesListView(TenantViewMixin, generics.ListAPIView):
    serializer_class = HistorialTransaccionListSerializer
    permission_classes = [IsAuthenticated, IsAdminOrVeterinarianForSales]
    pagination_class = HistorialTransaccionesPagination

    def get_queryset(self):
        return HistorialTransaccionesSelector.get_historial_queryset(
            veterinaria_id=self.get_tenant_id(),
            params=self.request.query_params,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            HistorialTransaccionesSelector.enrich_pagos(
                page,
                veterinaria_id=self.get_tenant_id(),
                include_items=False,
            )
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        pagos = list(queryset)
        HistorialTransaccionesSelector.enrich_pagos(
            pagos,
            veterinaria_id=self.get_tenant_id(),
            include_items=False,
        )
        serializer = self.get_serializer(pagos, many=True)
        return Response(serializer.data)


class HistorialTransaccionesDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, IsAdminOrVeterinarianForSales]

    def get(self, request, id_pago: int):
        pago = HistorialTransaccionesSelector.get_historial_detalle(
            veterinaria_id=self.get_tenant_id(),
            id_pago=id_pago,
        )
        if not pago:
            return Response(
                {"detail": "Transaccion no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = HistorialTransaccionDetailSerializer(pago)
        return Response(serializer.data)

