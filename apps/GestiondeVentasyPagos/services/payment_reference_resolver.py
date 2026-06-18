import logging
from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.GestiondeVentasyPagos.models import Venta
from apps.NotificacionesySeguimiento.models import Pedido
from apps.GestionServiciosyReserva.models import Cita
from apps.AutenticacionySeguridad.models import BillingDemoEvent, Suscripcion
from apps.GestionInventarioProveedores.models import PuntoInventario, StockPunto, MovimientoInventario
from apps.GestionInventarioProveedores.services.inventario_movimiento_service import InventoryMovementService
from apps.GestiondeVentasyPagos.services.carrito_service import CarritoService

logger = logging.getLogger(__name__)


class PaymentReferenceResolver:
    @classmethod
    @transaction.atomic
    def resolve_payment_approval(cls, *, tipo_referencia: str, referencia_id: int, tenant_id: int, user=None) -> None:
        """
        Actualiza el estado de la entidad correspondiente una vez que el pago ha sido aprobado.
        """
        logger.info("Resolving payment approval for %s #%s", tipo_referencia, referencia_id)

        if tipo_referencia == "VENTA_WEB":
            cls._resolve_venta_web(referencia_id=referencia_id, tenant_id=tenant_id)
        elif tipo_referencia == "PEDIDO_MOVIL":
            cls._resolve_pedido_movil(referencia_id=referencia_id, tenant_id=tenant_id, user=user)
        elif tipo_referencia == "CITA_SERVICIO":
            cls._resolve_cita_servicio(referencia_id=referencia_id, tenant_id=tenant_id)
        elif tipo_referencia == "SAAS_SUSCRIPCION":
            cls._resolve_saas_suscripcion(referencia_id=referencia_id)
        else:
            raise ValidationError(f"Tipo de referencia '{tipo_referencia}' no soportado.")

    @classmethod
    def _resolve_venta_web(cls, *, referencia_id: int, tenant_id: int) -> None:
        venta = Venta.objects.filter(id_venta=referencia_id, veterinaria_id=tenant_id).first()
        if not venta:
            raise ValidationError("Venta no encontrada para este tenant.")

        if venta.estado_venta == Venta.EstadoVenta.PAGADA:
            logger.info("Venta #%d ya está en estado PAGADA.", referencia_id)
            return

        venta.estado_venta = Venta.EstadoVenta.PAGADA
        venta.save(update_fields=["estado_venta", "fecha_actualizacion"])
        # IMPORTANTE: No descontar inventario aquí ya que la venta presencial lo descontó al crearse.
        logger.info("Venta #%d marcada como PAGADA con éxito.", referencia_id)

    @classmethod
    def _resolve_pedido_movil(cls, *, referencia_id: int, tenant_id: int, user=None) -> None:
        pedido = Pedido.objects.filter(id_pedido=referencia_id, veterinaria_id=tenant_id).first()
        if not pedido:
            raise ValidationError("Pedido no encontrado para este tenant.")

        if pedido.estado_pedido == "CONFIRMADO":
            logger.info("Pedido #%d ya está CONFIRMADO.", referencia_id)
            return

        # Volver a validar stock del pedido antes de proceder
        tiene_stock, result_or_msg = cls._validar_stock_pedido(pedido=pedido, tenant_id=tenant_id)
        if not tiene_stock:
            logger.warning("No se registró salida de inventario para Pedido #%d: %s", referencia_id, result_or_msg)
            # No confirmamos automáticamente; queda en revisión administrativa en estado PENDIENTE
            pedido.observacion = (pedido.observacion or "") + f" [REVISION ADMINISTRATIVA: Pago aprobado pero no hay stock suficiente para despachar: {result_or_msg}]"
            pedido.estado_pedido = "PENDIENTE"
        else:
            punto_almacen = result_or_msg
            # Registrar salida de inventario para los productos del pedido
            usuario_responsable = user or pedido.usuario
            for detalle in pedido.detalles.filter(estado=True):
                InventoryMovementService.register_movement(
                    veterinaria_id=tenant_id,
                    usuario=usuario_responsable,
                    producto=detalle.producto,
                    tipo=MovimientoInventario.TipoMovimiento.SALIDA,
                    cantidad=Decimal(str(detalle.cantidad)),
                    punto_origen=punto_almacen,
                    motivo=f"Despacho Pedido Móvil #{pedido.id_pedido}",
                )
            logger.info("Inventario descontado exitosamente para Pedido #%d.", referencia_id)
            pedido.estado_pedido = "CONFIRMADO"

        pedido.save(update_fields=["estado_pedido", "observacion", "fecha_actualizacion"])

        # Vaciar el carrito temporal del cliente
        try:
            CarritoService.vaciar_carrito(user=pedido.usuario, tenant_id=tenant_id)
            logger.info("Carrito temporal vaciado para el usuario del Pedido #%d.", referencia_id)
        except Exception as e:
            logger.exception("Error al vaciar carrito para el Pedido #%d: %s", referencia_id, str(e))

    @classmethod
    def _resolve_cita_servicio(cls, *, referencia_id: int, tenant_id: int) -> None:
        cita = Cita.objects.filter(id_cita=referencia_id, veterinaria_id=tenant_id).first()
        if not cita:
            raise ValidationError("Cita no encontrada para este tenant.")

        if cita.estado == Cita.EstadoChoices.CONFIRMADA:
            logger.info("Cita #%d ya está CONFIRMADA.", referencia_id)
            return

        cita.estado = Cita.EstadoChoices.CONFIRMADA
        cita.save(update_fields=["estado"])
        logger.info("Cita #%d marcada como CONFIRMADA.", referencia_id)

    @classmethod
    def _resolve_saas_suscripcion(cls, *, referencia_id: int) -> None:
        # Mantener intacto el flujo SaaS con BillingDemoEvent.
        # No reemplazamos BillingDemoEvent ni modificamos la activación o checkout.
        event = BillingDemoEvent.objects.filter(id_billing_demo_event=referencia_id).first()
        if not event:
            raise ValidationError("Evento de suscripción SaaS no encontrado.")
        logger.info("Confirmación del resolver para evento SaaS #%d completada.", referencia_id)

    @staticmethod
    def _validar_stock_pedido(*, pedido, tenant_id: int):
        punto_almacen = PuntoInventario.objects.filter(
            veterinaria_id=tenant_id,
            estado=True,
            tipo=PuntoInventario.TipoPunto.ALMACEN_GENERAL,
        ).order_by("id_punto").first()
        
        if not punto_almacen:
            return False, "No existe almacén principal configurado."

        for detalle in pedido.detalles.filter(estado=True):
            producto = detalle.producto
            stock = StockPunto.objects.filter(
                veterinaria_id=tenant_id,
                punto_inventario=punto_almacen,
                producto=producto,
            ).first()
            cantidad_disponible = stock.cantidad if stock else Decimal("0")
            if cantidad_disponible < Decimal(str(detalle.cantidad)):
                return False, f"Stock insuficiente para {producto.nombre} (Disponible: {cantidad_disponible}, Requerido: {detalle.cantidad})."
        
        return True, punto_almacen

