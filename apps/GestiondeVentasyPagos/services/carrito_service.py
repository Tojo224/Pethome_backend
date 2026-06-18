from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from rest_framework.exceptions import NotFound, ValidationError

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.GestionInventarioProveedores.models import StockPunto
from apps.GestiondeVentasyPagos.models import CarritoTemporal, DetalleCarritoTemporal


class CarritoService:
    @classmethod
    def obtener_o_crear_carrito_activo(cls, *, user, tenant_id: int) -> CarritoTemporal:
        cls._validar_contexto_cliente(user=user, tenant_id=tenant_id)
        try:
            carrito, _ = CarritoTemporal.objects.get_or_create(
                veterinaria_id=tenant_id,
                cliente=user,
                estado=True,
                estado_carrito=CarritoTemporal.EstadoCarrito.ACTIVO,
            )
        except IntegrityError:
            carrito = cls._obtener_carrito_activo(user=user, tenant_id=tenant_id)
            if not carrito:
                raise
        return carrito

    @classmethod
    def obtener_carrito(cls, *, user, tenant_id: int) -> CarritoTemporal:
        carrito = cls.obtener_o_crear_carrito_activo(user=user, tenant_id=tenant_id)
        cls.recalcular_totales(carrito=carrito)
        return cls._obtener_carrito_activo(user=user, tenant_id=tenant_id)

    @classmethod
    @transaction.atomic
    def agregar_item(cls, *, user, tenant_id: int, data: dict) -> CarritoTemporal:
        carrito = cls.obtener_o_crear_carrito_activo(user=user, tenant_id=tenant_id)
        tipo_item = data.get("tipo_item")

        if tipo_item == DetalleCarritoTemporal.TipoItem.PRODUCTO:
            cls._agregar_producto(carrito=carrito, tenant_id=tenant_id, data=data)
        elif tipo_item == DetalleCarritoTemporal.TipoItem.SERVICIO:
            cls._agregar_servicio(carrito=carrito, user=user, tenant_id=tenant_id, data=data)
        else:
            raise ValidationError({"tipo_item": "tipo_item no válido."})

        cls.recalcular_totales(carrito=carrito)
        return cls._obtener_carrito_activo(user=user, tenant_id=tenant_id)

    @classmethod
    @transaction.atomic
    def actualizar_cantidad(
        cls,
        *,
        user,
        tenant_id: int,
        detalle_id: int,
        cantidad: Decimal,
    ) -> CarritoTemporal:
        cls._validar_contexto_cliente(user=user, tenant_id=tenant_id)
        detalle = cls._obtener_detalle_activo(user=user, tenant_id=tenant_id, detalle_id=detalle_id)
        carrito = detalle.carrito

        precio_unitario = cls._resolver_precio_detalle(
            detalle=detalle,
            user=user,
            tenant_id=tenant_id,
            cantidad=cantidad,
        )
        detalle.cantidad = cantidad
        detalle.precio_unitario_estimado = precio_unitario
        detalle.subtotal_estimado = cantidad * precio_unitario
        detalle.save(update_fields=["cantidad", "precio_unitario_estimado", "subtotal_estimado", "fecha_actualizacion"])

        cls.recalcular_totales(carrito=carrito)
        return cls._obtener_carrito_activo(user=user, tenant_id=tenant_id)

    @classmethod
    @transaction.atomic
    def eliminar_item(cls, *, user, tenant_id: int, detalle_id: int) -> CarritoTemporal:
        cls._validar_contexto_cliente(user=user, tenant_id=tenant_id)
        detalle = cls._obtener_detalle_activo(user=user, tenant_id=tenant_id, detalle_id=detalle_id)
        carrito = detalle.carrito
        detalle.estado = False
        detalle.save(update_fields=["estado", "fecha_actualizacion"])

        cls.recalcular_totales(carrito=carrito)
        return cls._obtener_carrito_activo(user=user, tenant_id=tenant_id)

    @classmethod
    @transaction.atomic
    def vaciar_carrito(cls, *, user, tenant_id: int) -> None:
        carrito = cls.obtener_o_crear_carrito_activo(user=user, tenant_id=tenant_id)
        carrito.detalles.filter(estado=True).update(estado=False)
        carrito.subtotal_estimado = Decimal("0")
        carrito.total_estimado = Decimal("0")
        carrito.estado_carrito = CarritoTemporal.EstadoCarrito.VACIADO
        carrito.save(update_fields=["subtotal_estimado", "total_estimado", "estado_carrito", "fecha_actualizacion"])

    @classmethod
    def recalcular_totales(cls, *, carrito: CarritoTemporal) -> None:
        totales = carrito.detalles.filter(estado=True).aggregate(
            subtotal=Coalesce(Sum("subtotal_estimado"), Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2))
        )
        subtotal = totales["subtotal"] or Decimal("0")
        carrito.subtotal_estimado = subtotal
        carrito.total_estimado = subtotal
        carrito.estado_carrito = CarritoTemporal.EstadoCarrito.ACTIVO
        carrito.save(update_fields=["subtotal_estimado", "total_estimado", "estado_carrito", "fecha_actualizacion"])

    @staticmethod
    def _validar_contexto_cliente(*, user, tenant_id: int) -> None:
        if not tenant_id:
            raise ValidationError({"detail": "No se pudo resolver la veterinaria actual."})
        if not getattr(user, "is_active", False):
            raise ValidationError({"detail": "El usuario autenticado está inactivo."})
        if getattr(user, "veterinaria_id", None) != tenant_id:
            raise ValidationError({"detail": "No tienes acceso al tenant indicado."})

        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        if role_name != RoleEnum.CLIENT.value:
            raise ValidationError({"detail": "Solo clientes pueden gestionar carrito móvil."})

    @classmethod
    def _obtener_carrito_activo(cls, *, user, tenant_id: int) -> CarritoTemporal | None:
        return (
            CarritoTemporal.objects.select_related("veterinaria", "cliente")
            .prefetch_related("detalles", "detalles__producto", "detalles__servicio", "detalles__precio_servicio", "detalles__mascota")
            .filter(
                veterinaria_id=tenant_id,
                cliente=user,
                estado=True,
                estado_carrito=CarritoTemporal.EstadoCarrito.ACTIVO,
            )
            .first()
        )

    @staticmethod
    def _validar_producto_disponible(*, producto, tenant_id: int, cantidad: Decimal) -> Decimal:
        if not producto:
            raise ValidationError({"producto": "El producto es obligatorio para tipo PRODUCTO."})
        if producto.veterinaria_id != tenant_id:
            raise ValidationError({"producto": "El producto no pertenece a la veterinaria actual."})
        if not producto.estado:
            raise ValidationError({"producto": "El producto seleccionado está inactivo."})
        if not producto.visible_catalogo:
            raise ValidationError({"producto": "El producto no está disponible en catálogo."})
        if producto.precio_venta is None or producto.precio_venta <= 0:
            raise ValidationError({"producto": "El producto seleccionado no tiene un precio de venta válido."})

        stock_disponible = (
            StockPunto.objects.filter(
                veterinaria_id=tenant_id,
                producto_id=producto.id_producto,
                numero_lote__isnull=True,
            )
            .aggregate(total=Coalesce(Sum("cantidad"), Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2)))
            .get("total")
            or Decimal("0")
        )
        if stock_disponible <= 0:
            raise ValidationError({"producto": "Producto sin stock disponible."})
        if stock_disponible < cantidad:
            raise ValidationError({"producto": "Stock insuficiente disponible para el producto."})
        return producto.precio_venta

    @staticmethod
    def _validar_servicio_disponible(*, servicio, precio_servicio, mascota, user, tenant_id: int) -> Decimal:
        if not servicio:
            raise ValidationError({"servicio": "El servicio es obligatorio para tipo SERVICIO."})
        if not precio_servicio:
            raise ValidationError({"precio_servicio": "El precio_servicio es obligatorio para tipo SERVICIO."})
        if not mascota:
            raise ValidationError({"mascota": "La mascota es obligatoria para tipo SERVICIO."})

        if servicio.veterinaria_id != tenant_id or not servicio.estado:
            raise ValidationError({"servicio": "El servicio no es válido para la veterinaria actual."})
        if precio_servicio.veterinaria_id != tenant_id or not precio_servicio.estado:
            raise ValidationError({"precio_servicio": "El precio de servicio no es válido para la veterinaria actual."})
        if precio_servicio.servicio_id != servicio.id_servicio:
            raise ValidationError({"precio_servicio": "El precio de servicio no corresponde al servicio seleccionado."})
        if precio_servicio.precio is None or precio_servicio.precio <= 0:
            raise ValidationError({"precio_servicio": "El precio de servicio seleccionado debe ser mayor a cero."})
        if mascota.veterinaria_id != tenant_id:
            raise ValidationError({"mascota": "La mascota no pertenece a la veterinaria actual."})
        if mascota.usuario_id != user.id_usuario:
            raise ValidationError({"mascota": "La mascota no pertenece al cliente autenticado."})
        if not mascota.estado:
            raise ValidationError({"mascota": "La mascota seleccionada está inactiva."})
        return precio_servicio.precio

    @classmethod
    def _agregar_producto(cls, *, carrito: CarritoTemporal, tenant_id: int, data: dict) -> None:
        if data.get("servicio") or data.get("precio_servicio") or data.get("mascota"):
            raise ValidationError(
                {"detail": "No debes enviar servicio/precio_servicio/mascota para un detalle PRODUCTO."}
            )

        producto = data.get("producto")
        cantidad = data.get("cantidad")
        if cantidad is None or cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad del producto debe ser mayor a cero."})
        precio = cls._validar_producto_disponible(producto=producto, tenant_id=tenant_id, cantidad=cantidad)

        detalle = carrito.detalles.filter(
            estado=True,
            tipo_item=DetalleCarritoTemporal.TipoItem.PRODUCTO,
            producto=producto,
        ).first()
        if detalle:
            detalle.cantidad += cantidad
            cls._validar_producto_disponible(producto=producto, tenant_id=tenant_id, cantidad=detalle.cantidad)
            detalle.precio_unitario_estimado = precio
            detalle.subtotal_estimado = detalle.cantidad * precio
            detalle.observacion = data.get("observacion")
            detalle.save(
                update_fields=["cantidad", "precio_unitario_estimado", "subtotal_estimado", "observacion", "fecha_actualizacion"]
            )
            return

        DetalleCarritoTemporal.objects.create(
            carrito=carrito,
            tipo_item=DetalleCarritoTemporal.TipoItem.PRODUCTO,
            producto=producto,
            descripcion_item=producto.nombre,
            cantidad=cantidad,
            precio_unitario_estimado=precio,
            subtotal_estimado=cantidad * precio,
            observacion=data.get("observacion"),
        )

    @classmethod
    def _agregar_servicio(cls, *, carrito: CarritoTemporal, user, tenant_id: int, data: dict) -> None:
        if data.get("producto"):
            raise ValidationError({"detail": "No debes enviar producto para un detalle SERVICIO."})

        servicio = data.get("servicio")
        precio_servicio = data.get("precio_servicio")
        mascota = data.get("mascota")
        cantidad = data.get("cantidad") or Decimal("1")
        if cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad del servicio debe ser mayor a cero."})
        precio = cls._validar_servicio_disponible(
            servicio=servicio,
            precio_servicio=precio_servicio,
            mascota=mascota,
            user=user,
            tenant_id=tenant_id,
        )

        detalle = carrito.detalles.filter(
            estado=True,
            tipo_item=DetalleCarritoTemporal.TipoItem.SERVICIO,
            servicio=servicio,
            precio_servicio=precio_servicio,
            mascota=mascota,
        ).first()
        if detalle:
            detalle.cantidad += cantidad
            detalle.precio_unitario_estimado = precio
            detalle.subtotal_estimado = detalle.cantidad * precio
            detalle.observacion = data.get("observacion")
            detalle.save(
                update_fields=["cantidad", "precio_unitario_estimado", "subtotal_estimado", "observacion", "fecha_actualizacion"]
            )
            return

        DetalleCarritoTemporal.objects.create(
            carrito=carrito,
            tipo_item=DetalleCarritoTemporal.TipoItem.SERVICIO,
            servicio=servicio,
            precio_servicio=precio_servicio,
            mascota=mascota,
            descripcion_item=servicio.nombre,
            cantidad=cantidad,
            precio_unitario_estimado=precio,
            subtotal_estimado=cantidad * precio,
            observacion=data.get("observacion"),
        )

    @classmethod
    def _obtener_detalle_activo(cls, *, user, tenant_id: int, detalle_id: int) -> DetalleCarritoTemporal:
        detalle = (
            DetalleCarritoTemporal.objects.select_related(
                "carrito",
                "producto",
                "servicio",
                "precio_servicio",
                "mascota",
            )
            .filter(
                id_detalle_carrito=detalle_id,
                estado=True,
                carrito__veterinaria_id=tenant_id,
                carrito__cliente=user,
                carrito__estado=True,
                carrito__estado_carrito=CarritoTemporal.EstadoCarrito.ACTIVO,
            )
            .first()
        )
        if not detalle:
            raise NotFound("Item de carrito no encontrado.")
        return detalle

    @classmethod
    def _resolver_precio_detalle(
        cls,
        *,
        detalle: DetalleCarritoTemporal,
        user,
        tenant_id: int,
        cantidad: Decimal,
    ) -> Decimal:
        if detalle.tipo_item == DetalleCarritoTemporal.TipoItem.PRODUCTO:
            return cls._validar_producto_disponible(
                producto=detalle.producto,
                tenant_id=tenant_id,
                cantidad=cantidad,
            )
        return cls._validar_servicio_disponible(
            servicio=detalle.servicio,
            precio_servicio=detalle.precio_servicio,
            mascota=detalle.mascota,
            user=user,
            tenant_id=tenant_id,
        )
