from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.GestionInventarioProveedores.models import MovimientoInventario, PuntoInventario
from apps.GestionInventarioProveedores.serializers.inventario_movimiento_serializer import (
    MovimientoInventarioCreateSerializer,
    MovimientoInventarioSerializer,
)
from apps.GestionInventarioProveedores.services.inventario_movimiento_service import InventoryMovementService


class InventarioMovimientoViewSet(TenantViewMixin, viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "INV_PRODUCTOS"

    def list(self, request):
        tenant_id = self.get_tenant_id()
        queryset = MovimientoInventario.objects.select_related(
            "producto",
            "usuario",
            "punto_origen",
            "punto_destino",
        ).filter(veterinaria_id=tenant_id).order_by("-fecha_movimiento", "-id_movimiento")

        tipo = request.query_params.get("tipo")
        producto_id = request.query_params.get("id_producto")
        id_punto = request.query_params.get("id_punto")
        id_usuario = request.query_params.get("id_usuario")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        if id_punto:
            queryset = queryset.filter(Q(punto_origen_id=id_punto) | Q(punto_destino_id=id_punto))
        if id_usuario:
            queryset = queryset.filter(usuario_id=id_usuario)
        if fecha_desde:
            d = parse_date(fecha_desde)
            if d:
                queryset = queryset.filter(fecha_movimiento__date__gte=d)
        if fecha_hasta:
            d = parse_date(fecha_hasta)
            if d:
                queryset = queryset.filter(fecha_movimiento__date__lte=d)

        return Response(MovimientoInventarioSerializer(queryset, many=True).data)

    def retrieve(self, request, pk=None):
        tenant_id = self.get_tenant_id()
        movimiento = MovimientoInventario.objects.select_related(
            "producto",
            "usuario",
            "punto_origen",
            "punto_destino",
        ).filter(veterinaria_id=tenant_id, pk=pk).first()
        if not movimiento:
            return Response({"detail": "Movimiento no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MovimientoInventarioSerializer(movimiento).data)

    def create(self, request):
        tenant_id = self.get_tenant_id()
        serializer = MovimientoInventarioCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        punto_origen = data.get("punto_origen")
        punto_destino = data.get("punto_destino")

        # Bloqueo explícito para transferencias a unidad móvil inactiva.
        if punto_destino and punto_destino.tipo == PuntoInventario.TipoPunto.UNIDAD_MOVIL and not punto_destino.estado:
            return Response(
                {"detail": "No se puede transferir inventario a una unidad móvil inactiva."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        movimiento = InventoryMovementService.register_movement(
            veterinaria_id=tenant_id,
            usuario=request.user,
            producto=data["producto"],
            tipo=data["tipo"],
            cantidad=data["cantidad"],
            numero_lote=data.get("numero_lote"),
            fecha_vencimiento_lote=data.get("fecha_vencimiento_lote"),
            punto_origen=punto_origen,
            punto_destino=punto_destino,
            motivo=data.get("motivo"),
        )

        return Response(
            {
                "message": "Movimiento registrado correctamente",
                "movimiento": MovimientoInventarioSerializer(movimiento).data,
            },
            status=status.HTTP_201_CREATED,
        )
