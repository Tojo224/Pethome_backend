from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.GestionInventarioProveedores.models import PuntoInventario, StockPunto
from apps.GestionInventarioProveedores.serializers.inventario_stock_serializer import StockPuntoSerializer


class InventarioStockViewSet(TenantViewMixin, viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "INV_PRODUCTOS"

    def general(self, request):
        tenant_id = self.get_tenant_id()
        queryset = StockPunto.objects.select_related(
            "producto",
            "producto__categoria_producto",
            "punto_inventario",
        ).filter(
            veterinaria_id=tenant_id,
            punto_inventario__tipo=PuntoInventario.TipoPunto.ALMACEN_GENERAL,
        )
        queryset = self._apply_common_filters(request, queryset)
        return Response(StockPuntoSerializer(queryset, many=True).data)

    def unidades_moviles(self, request):
        tenant_id = self.get_tenant_id()
        queryset = StockPunto.objects.select_related(
            "producto",
            "producto__categoria_producto",
            "punto_inventario",
        ).filter(
            veterinaria_id=tenant_id,
            punto_inventario__tipo=PuntoInventario.TipoPunto.UNIDAD_MOVIL,
        )
        queryset = self._apply_common_filters(request, queryset)
        return Response(StockPuntoSerializer(queryset, many=True).data)

    def alertas(self, request):
        tenant_id = self.get_tenant_id()
        estado = request.query_params.get("estado")
        queryset = StockPunto.objects.select_related(
            "producto",
            "producto__categoria_producto",
            "punto_inventario",
        ).filter(veterinaria_id=tenant_id)

        if estado == "AGOTADO":
            queryset = queryset.filter(cantidad__lte=0)
        elif estado == "STOCK_BAJO":
            queryset = queryset.filter(cantidad__gt=0, cantidad__lte=F("cantidad_minima"))
        else:
            queryset = queryset.filter(Q(cantidad__lte=0) | Q(cantidad__lte=F("cantidad_minima")))

        return Response(StockPuntoSerializer(queryset, many=True).data)

    def disponibilidad(self, request, pk=None):
        tenant_id = self.get_tenant_id()
        resumen = (
            StockPunto.objects.filter(veterinaria_id=tenant_id, producto_id=pk)
            .values("producto_id", "producto__nombre")
            .annotate(
                stock_total=Coalesce(
                    Sum("cantidad"),
                    Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
                ),
                stock_general=Coalesce(
                    Sum(
                        "cantidad",
                        filter=Q(punto_inventario__tipo=PuntoInventario.TipoPunto.ALMACEN_GENERAL),
                    ),
                    Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
                ),
                stock_movil=Coalesce(
                    Sum(
                        "cantidad",
                        filter=Q(punto_inventario__tipo=PuntoInventario.TipoPunto.UNIDAD_MOVIL),
                    ),
                    Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
                ),
            )
            .order_by("producto_id")
            .first()
        )
        if not resumen:
            return Response(
                {
                    "id_producto": int(pk),
                    "stock_total": 0,
                    "stock_general": 0,
                    "stock_movil": 0,
                }
            )
        return Response(resumen)

    def _apply_common_filters(self, request, queryset):
        search = request.query_params.get("search")
        id_categoria = request.query_params.get("id_categoria_producto")
        id_punto = request.query_params.get("id_punto")

        if search:
            queryset = queryset.filter(
                Q(producto__nombre__icontains=search)
                | Q(producto__descripcion__icontains=search)
                | Q(punto_inventario__nombre__icontains=search)
            )
        if id_categoria:
            queryset = queryset.filter(producto__categoria_producto_id=id_categoria)
        if id_punto:
            queryset = queryset.filter(punto_inventario_id=id_punto)
        return queryset
