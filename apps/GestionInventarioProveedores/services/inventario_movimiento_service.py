from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.GestionInventarioProveedores.models import (
    MovimientoInventario,
    PuntoInventario,
    StockPunto,
)


class InventoryMovementService:
    DECREMENT_TYPES = {
        MovimientoInventario.TipoMovimiento.SALIDA,
        MovimientoInventario.TipoMovimiento.CONSUMO,
    }

    INCREMENT_TYPES = {
        MovimientoInventario.TipoMovimiento.ENTRADA,
        MovimientoInventario.TipoMovimiento.REPOSICION,
    }

    @classmethod
    @transaction.atomic
    def register_movement(
        cls,
        *,
        veterinaria_id: int,
        usuario,
        producto,
        tipo: str,
        cantidad: Decimal,
        punto_origen: PuntoInventario | None = None,
        punto_destino: PuntoInventario | None = None,
        motivo: str | None = None,
    ) -> MovimientoInventario:
        if cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad debe ser mayor a cero."})

        cls._validate_tenant(veterinaria_id, producto, punto_origen, punto_destino)
        cls._validate_flow(tipo, punto_origen, punto_destino)

        if tipo in cls.DECREMENT_TYPES:
            return cls._apply_decrement(
                veterinaria_id=veterinaria_id,
                usuario=usuario,
                producto=producto,
                tipo=tipo,
                cantidad=cantidad,
                punto_origen=punto_origen,
                motivo=motivo,
            )

        if tipo in cls.INCREMENT_TYPES:
            return cls._apply_increment(
                veterinaria_id=veterinaria_id,
                usuario=usuario,
                producto=producto,
                tipo=tipo,
                cantidad=cantidad,
                punto_destino=punto_destino,
                motivo=motivo,
            )

        if tipo == MovimientoInventario.TipoMovimiento.TRANSFERENCIA:
            return cls._apply_transfer(
                veterinaria_id=veterinaria_id,
                usuario=usuario,
                producto=producto,
                cantidad=cantidad,
                punto_origen=punto_origen,
                punto_destino=punto_destino,
                motivo=motivo,
            )

        if tipo == MovimientoInventario.TipoMovimiento.DEVOLUCION:
            return cls._apply_transfer(
                veterinaria_id=veterinaria_id,
                usuario=usuario,
                producto=producto,
                cantidad=cantidad,
                punto_origen=punto_origen,
                punto_destino=punto_destino,
                motivo=motivo,
                movimiento_tipo=MovimientoInventario.TipoMovimiento.DEVOLUCION,
            )

        if tipo == MovimientoInventario.TipoMovimiento.AJUSTE:
            return cls._apply_adjustment(
                veterinaria_id=veterinaria_id,
                usuario=usuario,
                producto=producto,
                cantidad=cantidad,
                punto_origen=punto_origen,
                punto_destino=punto_destino,
                motivo=motivo,
            )

        raise ValidationError({"tipo": "Tipo de movimiento no soportado."})

    @classmethod
    def _validate_tenant(cls, veterinaria_id, producto, punto_origen, punto_destino):
        if producto.veterinaria_id != veterinaria_id:
            raise ValidationError({"id_producto": "El producto no pertenece a la veterinaria autenticada."})
        for field, punto in [("id_punto_origen", punto_origen), ("id_punto_destino", punto_destino)]:
            if punto and punto.veterinaria_id != veterinaria_id:
                raise ValidationError({field: "El punto no pertenece a la veterinaria autenticada."})

    @classmethod
    def _validate_flow(cls, tipo, punto_origen, punto_destino):
        if tipo in cls.DECREMENT_TYPES and not punto_origen:
            raise ValidationError({"id_punto_origen": "Este movimiento requiere punto de origen."})
        if tipo in cls.INCREMENT_TYPES and not punto_destino:
            raise ValidationError({"id_punto_destino": "Este movimiento requiere punto de destino."})
        if tipo in {MovimientoInventario.TipoMovimiento.TRANSFERENCIA, MovimientoInventario.TipoMovimiento.DEVOLUCION}:
            if not punto_origen or not punto_destino:
                raise ValidationError({"detail": "Transferencia/devolucion requiere origen y destino."})
            if punto_origen.id_punto == punto_destino.id_punto:
                raise ValidationError({"detail": "Origen y destino no pueden ser iguales."})

    @classmethod
    def _get_stock_locked(cls, *, veterinaria_id, producto, punto):
        stock, _ = StockPunto.objects.select_for_update().get_or_create(
            veterinaria_id=veterinaria_id,
            producto=producto,
            punto_inventario=punto,
            defaults={"cantidad": 0, "cantidad_minima": 0},
        )
        return stock

    @classmethod
    def _apply_decrement(cls, *, veterinaria_id, usuario, producto, tipo, cantidad, punto_origen, motivo):
        stock = cls._get_stock_locked(veterinaria_id=veterinaria_id, producto=producto, punto=punto_origen)
        if stock.cantidad < cantidad:
            raise ValidationError({"detail": "Stock insuficiente para realizar el movimiento."})
        anterior = stock.cantidad
        stock.cantidad = anterior - cantidad
        stock.save(update_fields=["cantidad", "fecha_actualizacion"])
        return MovimientoInventario.objects.create(
            veterinaria_id=veterinaria_id,
            producto=producto,
            usuario=usuario,
            punto_origen=punto_origen,
            tipo=tipo,
            cantidad=cantidad,
            cantidad_anterior=anterior,
            cantidad_posterior=stock.cantidad,
            motivo=motivo,
        )

    @classmethod
    def _apply_increment(cls, *, veterinaria_id, usuario, producto, tipo, cantidad, punto_destino, motivo):
        stock = cls._get_stock_locked(veterinaria_id=veterinaria_id, producto=producto, punto=punto_destino)
        anterior = stock.cantidad
        stock.cantidad = anterior + cantidad
        stock.save(update_fields=["cantidad", "fecha_actualizacion"])
        return MovimientoInventario.objects.create(
            veterinaria_id=veterinaria_id,
            producto=producto,
            usuario=usuario,
            punto_destino=punto_destino,
            tipo=tipo,
            cantidad=cantidad,
            cantidad_anterior=anterior,
            cantidad_posterior=stock.cantidad,
            motivo=motivo,
        )

    @classmethod
    def _apply_transfer(
        cls,
        *,
        veterinaria_id,
        usuario,
        producto,
        cantidad,
        punto_origen,
        punto_destino,
        motivo,
        movimiento_tipo=MovimientoInventario.TipoMovimiento.TRANSFERENCIA,
    ):
        stock_origen = cls._get_stock_locked(veterinaria_id=veterinaria_id, producto=producto, punto=punto_origen)
        if stock_origen.cantidad < cantidad:
            raise ValidationError({"detail": "Stock insuficiente para realizar el movimiento."})
        stock_destino = cls._get_stock_locked(veterinaria_id=veterinaria_id, producto=producto, punto=punto_destino)

        anterior_origen = stock_origen.cantidad
        stock_origen.cantidad = anterior_origen - cantidad
        stock_origen.save(update_fields=["cantidad", "fecha_actualizacion"])

        anterior_destino = stock_destino.cantidad
        stock_destino.cantidad = anterior_destino + cantidad
        stock_destino.save(update_fields=["cantidad", "fecha_actualizacion"])

        return MovimientoInventario.objects.create(
            veterinaria_id=veterinaria_id,
            producto=producto,
            usuario=usuario,
            punto_origen=punto_origen,
            punto_destino=punto_destino,
            tipo=movimiento_tipo,
            cantidad=cantidad,
            cantidad_anterior=anterior_origen,
            cantidad_posterior=stock_origen.cantidad,
            motivo=motivo,
        )

    @classmethod
    def _apply_adjustment(
        cls,
        *,
        veterinaria_id,
        usuario,
        producto,
        cantidad,
        punto_origen,
        punto_destino,
        motivo,
    ):
        punto = punto_destino or punto_origen
        if not punto:
            raise ValidationError({"detail": "El ajuste requiere al menos un punto de inventario."})
        stock = cls._get_stock_locked(veterinaria_id=veterinaria_id, producto=producto, punto=punto)
        anterior = stock.cantidad
        posterior = anterior + cantidad
        if posterior < 0:
            raise ValidationError({"detail": "El ajuste no puede dejar stock negativo."})
        stock.cantidad = posterior
        stock.save(update_fields=["cantidad", "fecha_actualizacion"])
        return MovimientoInventario.objects.create(
            veterinaria_id=veterinaria_id,
            producto=producto,
            usuario=usuario,
            punto_origen=punto_origen,
            punto_destino=punto_destino,
            tipo=MovimientoInventario.TipoMovimiento.AJUSTE,
            cantidad=cantidad,
            cantidad_anterior=anterior,
            cantidad_posterior=posterior,
            motivo=motivo,
        )
