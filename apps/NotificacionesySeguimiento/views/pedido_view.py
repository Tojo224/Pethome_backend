from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..filters import (
    ALLOWED_PEDIDO_FILTER_PARAMS,
    PedidoFilter,
    get_unknown_filter_params,
)
from ..permissions import HasVeterinariaWithoutSuperadmin
from ..selectors import PedidoSelector
from ..serializers import PedidoDetailSerializer, PedidoListSerializer


class PedidoListView(APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaWithoutSuperadmin]

    def get(self, request):
        unknown_params = get_unknown_filter_params(request.query_params, ALLOWED_PEDIDO_FILTER_PARAMS)
        if unknown_params:
            return Response(
                {
                    "detail": "Parametros de filtro invalidos.",
                    "errors": {
                        "query_params": [
                            f"Parametros no permitidos: {', '.join(unknown_params)}."
                        ]
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = PedidoSelector.get_pedidos_for_user(request.user)
        filterset = PedidoFilter(request.GET, queryset=queryset)

        if not filterset.is_valid():
            return Response(
                {"detail": "Parametros de filtro invalidos.", "errors": filterset.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PedidoListSerializer(filterset.qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        user = request.user
        tenant_id = getattr(user, "veterinaria_id", None)
        if not tenant_id:
            return Response({"detail": "No se pudo resolver la veterinaria del usuario."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 1. Validar rol de cliente
        from apps.AutenticacionySeguridad.enums.roles import RoleEnum
        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        if role_name != RoleEnum.CLIENT.value:
            return Response({"detail": "Solo clientes pueden realizar pedidos móviles."}, status=status.HTTP_403_FORBIDDEN)

        # 2. Obtener carrito activo
        from apps.GestiondeVentasyPagos.models import CarritoTemporal, DetalleCarritoTemporal
        carrito = CarritoTemporal.objects.prefetch_related("detalles__producto").filter(
            veterinaria_id=tenant_id,
            cliente=user,
            estado=True,
            estado_carrito=CarritoTemporal.EstadoCarrito.ACTIVO,
        ).first()

        if not carrito or not carrito.detalles.filter(estado=True).exists():
            return Response({"detail": "El carrito está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        # Leer body params
        tipo_entrega = request.data.get("tipo_entrega", "DOMICILIO")
        direccion_entrega = request.data.get("direccion_entrega")
        observacion = request.data.get("observacion", "")

        if tipo_entrega not in ["DOMICILIO", "RECOJO"]:
            return Response({"tipo_entrega": "Tipo de entrega no válido."}, status=status.HTTP_400_BAD_REQUEST)
        if tipo_entrega == "DOMICILIO" and not direccion_entrega:
            return Response({"direccion_entrega": "La dirección de entrega es obligatoria para pedidos a domicilio."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Validar stock antes de crear/actualizar el pedido (Criterio de aceptación #4)
        from apps.GestionInventarioProveedores.models import PuntoInventario, StockPunto
        from decimal import Decimal
        punto_almacen = PuntoInventario.objects.filter(
            veterinaria_id=tenant_id,
            estado=True,
            tipo=PuntoInventario.TipoPunto.ALMACEN_GENERAL,
        ).order_by("id_punto").first()
        
        if not punto_almacen:
            return Response({"detail": "No existe almacén principal configurado en la veterinaria para despachar productos."}, status=status.HTTP_400_BAD_REQUEST)

        for det in carrito.detalles.filter(estado=True):
            if det.tipo_item == DetalleCarritoTemporal.TipoItem.PRODUCTO:
                stock = StockPunto.objects.filter(
                    veterinaria_id=tenant_id,
                    punto_inventario=punto_almacen,
                    producto=det.producto,
                    numero_lote__isnull=True,
                ).first()
                cant_disponible = stock.cantidad if stock else Decimal("0")
                if cant_disponible < det.cantidad:
                    return Response(
                        {"detail": f"Stock insuficiente para el producto '{det.producto.nombre}'. Disponible: {cant_disponible}, Requerido: {det.cantidad}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Calcular totales
        from apps.NotificacionesySeguimiento.models import Pedido, DetallePedido
        costo_envio = Decimal("10.00") if tipo_entrega == "DOMICILIO" else Decimal("0.00")
        subtotal = carrito.total_estimado
        total = subtotal + costo_envio

        # 4. Comprobar si ya existe un pedido PENDIENTE para este cliente/tenant
        pedido_existente = Pedido.objects.filter(
            usuario=user,
            veterinaria_id=tenant_id,
            estado_pedido="PENDIENTE",
            estado=True
        ).first()

        if pedido_existente:
            # Reutilizar y actualizar el pedido existente con el carrito actual
            pedido_existente.detalles.all().delete()
            pedido_existente.tipo_entrega = tipo_entrega
            pedido_existente.direccion_entrega = direccion_entrega if tipo_entrega == "DOMICILIO" else None
            pedido_existente.observacion = observacion
            pedido_existente.subtotal = subtotal
            pedido_existente.costo_envio = costo_envio
            pedido_existente.total = total
            pedido_existente.save()

            # Crear detalles actualizados
            for det in carrito.detalles.filter(estado=True):
                if det.tipo_item == DetalleCarritoTemporal.TipoItem.PRODUCTO:
                    DetallePedido.objects.create(
                        pedido=pedido_existente,
                        producto=det.producto,
                        cantidad=int(det.cantidad),
                        precio_unitario=det.precio_unitario_estimado,
                        subtotal=det.subtotal_estimado,
                        observacion=det.observacion,
                    )
            
            serializer = PedidoDetailSerializer(pedido_existente, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        # 5. Crear el Pedido nuevo si no existía uno pendiente
        pedido = Pedido.objects.create(
            usuario=user,
            veterinaria_id=tenant_id,
            direccion_entrega=direccion_entrega if tipo_entrega == "DOMICILIO" else None,
            tipo_entrega=tipo_entrega,
            estado_pedido="PENDIENTE",
            subtotal=subtotal,
            costo_envio=costo_envio,
            total=total,
            observacion=observacion,
        )

        # Crear detalles
        for det in carrito.detalles.filter(estado=True):
            if det.tipo_item == DetalleCarritoTemporal.TipoItem.PRODUCTO:
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=det.producto,
                    cantidad=int(det.cantidad),
                    precio_unitario=det.precio_unitario_estimado,
                    subtotal=det.subtotal_estimado,
                    observacion=det.observacion,
                )

        serializer = PedidoDetailSerializer(pedido, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PedidoDetailView(APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaWithoutSuperadmin]

    def get(self, request, id_pedido):
        pedido = PedidoSelector.get_pedido_detail_for_user(request.user, id_pedido)
        if pedido is None:
            return Response(
                {"detail": "Pedido no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PedidoDetailSerializer(pedido, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
