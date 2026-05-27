from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.GestiondeVentasyPagos.permissions import IsAdminOrVeterinarianForSales
from apps.GestiondeVentasyPagos.selectors import VentaSelector
from apps.GestiondeVentasyPagos.serializers import (
    VentaCreateSerializer,
    VentaDetailSerializer,
    VentaListSerializer,
)
from apps.GestiondeVentasyPagos.services import VentaService


class VentaViewSet(TenantViewMixin, viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrVeterinarianForSales]

    def list(self, request):
        tenant_id = self.get_tenant_id()
        queryset = VentaSelector.get_ventas_by_tenant(tenant_id)
        queryset = self._apply_filters(queryset, request)
        return Response(VentaListSerializer(queryset, many=True).data)

    def retrieve(self, request, pk=None):
        tenant_id = self.get_tenant_id()
        venta = VentaSelector.get_venta_detail(tenant_id, int(pk))
        if not venta:
            return Response({"detail": "Venta no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(VentaDetailSerializer(venta).data)

    def create(self, request):
        tenant_id = self.get_tenant_id()
        serializer = VentaCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        venta = VentaService.crear_venta_presencial(
            tenant_id=tenant_id,
            usuario=request.user,
            validated_data=serializer.validated_data,
        )
        venta = VentaSelector.get_venta_detail(tenant_id, venta.id_venta)
        return Response(VentaDetailSerializer(venta).data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _apply_filters(queryset, request):
        estado_venta = request.query_params.get("estado_venta")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        cliente = request.query_params.get("cliente")
        mascota = request.query_params.get("mascota")

        if estado_venta:
            queryset = queryset.filter(estado_venta=estado_venta)
        if cliente:
            queryset = queryset.filter(cliente_id=cliente)
        if mascota:
            queryset = queryset.filter(mascota_id=mascota)
        if fecha_desde:
            fecha = parse_date(fecha_desde)
            if fecha:
                queryset = queryset.filter(fecha_venta__date__gte=fecha)
        if fecha_hasta:
            fecha = parse_date(fecha_hasta)
            if fecha:
                queryset = queryset.filter(fecha_venta__date__lte=fecha)
        return queryset
