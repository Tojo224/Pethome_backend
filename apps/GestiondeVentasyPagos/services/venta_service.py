from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.GestionClientesyMascotas.models import Mascota
from apps.GestionInventarioProveedores.models import MovimientoInventario, PuntoInventario, StockPunto
from apps.GestionInventarioProveedores.services.inventario_movimiento_service import InventoryMovementService
from apps.GestiondeVentasyPagos.models import DetalleVenta, Venta


class VentaService:
    @classmethod
    @transaction.atomic
    def crear_venta_presencial(cls, *, tenant_id: int, usuario, validated_data: dict) -> Venta:
        if not tenant_id:
            raise ValidationError({"detail": "No se pudo resolver la veterinaria actual."})

        cls._validar_rol(usuario)

        cliente = validated_data.get("cliente")
        mascota = validated_data.get("mascota")
        observacion = validated_data.get("observacion")
        detalles_payload = validated_data.get("detalles", [])

        cls._validar_cliente(cliente=cliente, tenant_id=tenant_id)

        detalles_normalizados, cantidades_producto, incluye_servicios = cls._normalizar_detalles(
            tenant_id=tenant_id,
            detalles_payload=detalles_payload,
        )

        cls._validar_mascota(
            mascota=mascota,
            cliente=cliente,
            tenant_id=tenant_id,
            mascota_obligatoria=incluye_servicios,
        )

        punto_almacen = None
        if cantidades_producto:
            punto_almacen = cls._obtener_almacen_principal(tenant_id=tenant_id)
            cls._validar_stock_por_producto(
                tenant_id=tenant_id,
                punto_almacen=punto_almacen,
                cantidades_producto=cantidades_producto,
            )

        venta = Venta.objects.create(
            veterinaria_id=tenant_id,
            usuario_responsable=usuario,
            cliente=cliente,
            mascota=mascota,
            observacion=observacion,
            estado_venta=Venta.EstadoVenta.PENDIENTE_COBRO,
        )

        total = Decimal("0")

        for item in detalles_normalizados:
            detalle = DetalleVenta.objects.create(
                venta=venta,
                tipo_item=item["tipo_item"],
                producto=item.get("producto"),
                servicio=item.get("servicio"),
                precio_servicio=item.get("precio_servicio"),
                descripcion_item=item["descripcion_item"],
                cantidad=item["cantidad"],
                precio_unitario=item["precio_unitario"],
                subtotal=item["subtotal"],
                observacion=item.get("observacion"),
            )
            total += detalle.subtotal

            if item["tipo_item"] == DetalleVenta.TipoItem.PRODUCTO:
                InventoryMovementService.register_movement(
                    veterinaria_id=tenant_id,
                    usuario=usuario,
                    producto=item["producto"],
                    tipo=MovimientoInventario.TipoMovimiento.SALIDA,
                    cantidad=item["cantidad"],
                    punto_origen=punto_almacen,
                    motivo="Venta presencial CU26",
                )

        venta.subtotal = total
        venta.total = total
        venta.save(update_fields=["subtotal", "total", "fecha_actualizacion"])

        return venta

    @staticmethod
    def _validar_rol(usuario):
        if getattr(usuario, "is_superuser", False):
            return

        rol = (getattr(getattr(usuario, "role", None), "nombre", "") or "").upper()
        roles_permitidos = {
            RoleEnum.ADMIN.value,
            RoleEnum.VETERINARIAN.value,
        }
        if rol not in roles_permitidos:
            raise ValidationError({"detail": "No tienes permisos para registrar ventas presenciales."})

    @staticmethod
    def _validar_cliente(*, cliente, tenant_id):
        if not cliente:
            return

        if not cliente.is_active:
            raise ValidationError({"cliente": "El cliente debe estar activo."})
        if cliente.veterinaria_id != tenant_id:
            raise ValidationError({"cliente": "El cliente no pertenece a la veterinaria actual."})

        rol_cliente = (getattr(getattr(cliente, "role", None), "nombre", "") or "").upper()
        if rol_cliente != RoleEnum.CLIENT.value:
            raise ValidationError({"cliente": "El usuario indicado no tiene rol de cliente."})

    @classmethod
    def _normalizar_detalles(cls, *, tenant_id, detalles_payload):
        if not detalles_payload:
            raise ValidationError({"detalles": "Debes registrar al menos un detalle."})

        normalizados = []
        cantidades_producto = defaultdict(lambda: Decimal("0"))
        incluye_servicios = False

        for idx, detalle in enumerate(detalles_payload, start=1):
            tipo_item = detalle.get("tipo_item")
            observacion = detalle.get("observacion")

            if tipo_item == DetalleVenta.TipoItem.PRODUCTO:
                producto = detalle.get("producto")
                if not producto:
                    raise ValidationError({f"detalles[{idx}]": "El producto es obligatorio para tipo PRODUCTO."})
                if detalle.get("servicio") or detalle.get("precio_servicio"):
                    raise ValidationError(
                        {f"detalles[{idx}]": "No debes enviar servicio/precio_servicio para un detalle PRODUCTO."}
                    )
                if producto.veterinaria_id != tenant_id:
                    raise ValidationError({f"detalles[{idx}]": "El producto no pertenece a la veterinaria actual."})
                if not producto.estado:
                    raise ValidationError({f"detalles[{idx}]": "El producto seleccionado está inactivo."})
                if producto.precio_venta is None or producto.precio_venta <= 0:
                    raise ValidationError(
                        {f"detalles[{idx}]": "El producto seleccionado no tiene un precio de venta válido."}
                    )

                cantidad = detalle.get("cantidad")
                if cantidad is None or cantidad <= 0:
                    raise ValidationError({f"detalles[{idx}]": "La cantidad del producto debe ser mayor a cero."})

                subtotal = cantidad * producto.precio_venta
                cantidades_producto[producto.id_producto] += cantidad
                normalizados.append(
                    {
                        "tipo_item": DetalleVenta.TipoItem.PRODUCTO,
                        "producto": producto,
                        "cantidad": cantidad,
                        "precio_unitario": producto.precio_venta,
                        "subtotal": subtotal,
                        "descripcion_item": producto.nombre,
                        "observacion": observacion,
                    }
                )
                continue

            if tipo_item == DetalleVenta.TipoItem.SERVICIO:
                incluye_servicios = True
                servicio = detalle.get("servicio")
                precio_servicio = detalle.get("precio_servicio")
                if not servicio:
                    raise ValidationError({f"detalles[{idx}]": "El servicio es obligatorio para tipo SERVICIO."})
                if not precio_servicio:
                    raise ValidationError(
                        {f"detalles[{idx}]": "El precio_servicio es obligatorio para tipo SERVICIO."}
                    )
                if detalle.get("producto"):
                    raise ValidationError({f"detalles[{idx}]": "No debes enviar producto para un detalle SERVICIO."})

                if servicio.veterinaria_id != tenant_id or not servicio.estado:
                    raise ValidationError({f"detalles[{idx}]": "El servicio no es válido para la veterinaria actual."})
                if precio_servicio.veterinaria_id != tenant_id or not precio_servicio.estado:
                    raise ValidationError(
                        {f"detalles[{idx}]": "El precio de servicio no es válido para la veterinaria actual."}
                    )
                if precio_servicio.servicio_id != servicio.id_servicio:
                    raise ValidationError(
                        {f"detalles[{idx}]": "El precio de servicio no corresponde al servicio seleccionado."}
                    )
                if precio_servicio.precio <= 0:
                    raise ValidationError(
                        {f"detalles[{idx}]": "El precio de servicio seleccionado debe ser mayor a cero."}
                    )

                cantidad = detalle.get("cantidad")
                if cantidad is None:
                    cantidad = Decimal("1")
                if cantidad <= 0:
                    raise ValidationError({f"detalles[{idx}]": "La cantidad del servicio debe ser mayor a cero."})

                subtotal = cantidad * precio_servicio.precio
                normalizados.append(
                    {
                        "tipo_item": DetalleVenta.TipoItem.SERVICIO,
                        "servicio": servicio,
                        "precio_servicio": precio_servicio,
                        "cantidad": cantidad,
                        "precio_unitario": precio_servicio.precio,
                        "subtotal": subtotal,
                        "descripcion_item": servicio.nombre,
                        "observacion": observacion,
                    }
                )
                continue

            raise ValidationError({f"detalles[{idx}]": "tipo_item no válido."})

        return normalizados, cantidades_producto, incluye_servicios

    @staticmethod
    def _validar_mascota(*, mascota: Mascota | None, cliente, tenant_id, mascota_obligatoria):
        if mascota_obligatoria and not mascota:
            raise ValidationError({"mascota": "La mascota es obligatoria cuando la venta incluye servicios."})

        if not mascota:
            return

        if not mascota.estado:
            raise ValidationError({"mascota": "La mascota seleccionada está inactiva."})
        if mascota.veterinaria_id != tenant_id:
            raise ValidationError({"mascota": "La mascota no pertenece a la veterinaria actual."})
        if cliente and mascota.usuario_id != cliente.id_usuario:
            raise ValidationError({"mascota": "La mascota no pertenece al cliente indicado."})

    @staticmethod
    def _obtener_almacen_principal(*, tenant_id):
        punto = PuntoInventario.objects.filter(
            veterinaria_id=tenant_id,
            estado=True,
            tipo=PuntoInventario.TipoPunto.ALMACEN_GENERAL,
        ).order_by("id_punto").first()
        if not punto:
            raise ValidationError(
                {"detail": "No existe almacén principal configurado para registrar la venta."}
            )
        return punto

    @staticmethod
    def _validar_stock_por_producto(*, tenant_id, punto_almacen, cantidades_producto):
        productos = [pid for pid in cantidades_producto.keys()]
        stocks = StockPunto.objects.select_for_update().filter(
            veterinaria_id=tenant_id,
            punto_inventario=punto_almacen,
            producto_id__in=productos,
        )
        stock_map = {stock.producto_id: stock for stock in stocks}

        for producto_id, cantidad_requerida in cantidades_producto.items():
            stock = stock_map.get(producto_id)
            cantidad_disponible = stock.cantidad if stock else Decimal("0")
            if cantidad_disponible < cantidad_requerida:
                raise ValidationError(
                    {
                        "detail": (
                            f"Stock insuficiente para el producto {producto_id} en el almacén principal."
                        )
                    }
                )
