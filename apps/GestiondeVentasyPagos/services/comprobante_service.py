import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError, PermissionDenied

from apps.GestiondeVentasyPagos.models import Pago, ComprobantePago, Venta
from apps.NotificacionesySeguimiento.models import Pedido
from apps.GestionServiciosyReserva.models import Cita
from apps.AutenticacionySeguridad.models import BillingDemoEvent, Veterinaria

logger = logging.getLogger(__name__)


class ComprobanteService:
    @classmethod
    @transaction.atomic
    def generar_comprobante(cls, *, pago: Pago) -> ComprobantePago:
        """
        Genera un comprobante de pago correlativo tras verificarse que el pago está PAGADO.
        """
        if pago.estado_pago != Pago.EstadoPago.PAGADO:
            raise ValidationError("No se puede generar un comprobante para un pago que no está PAGADO.")

        # Verificar si ya existe un comprobante para este pago
        if hasattr(pago, "comprobante") and pago.comprobante:
            logger.info("Comprobante ya existe para el Pago #%d", pago.id_pago)
            return pago.comprobante

        tenant_id = pago.veterinaria_id
        
        # Generar número correlativo por veterinaria
        numero_comprobante = cls._generar_siguiente_correlativo(tenant_id=tenant_id)

        # Construir el snapshot de detalles cobrados
        detalle_items = cls._construir_detalle_items(pago=pago)

        tipo_comprobante = ComprobantePago.TipoComprobante.RECIBO
        # Si tiene NIT o razón social, podríamos marcarlo como FACTURA si fuera necesario,
        # pero por defecto usaremos RECIBO o según prefiera.

        comprobante = ComprobantePago.objects.create(
            veterinaria=pago.veterinaria,
            pago=pago,
            numero_comprobante=numero_comprobante,
            tipo_comprobante=tipo_comprobante,
            monto=pago.monto,
            metodo_pago=pago.metodo_pago,
            detalle_items=detalle_items,
            estado=ComprobantePago.EstadoComprobante.EMITIDO,
        )

        logger.info("Comprobante %s generado con éxito para Pago #%d", numero_comprobante, pago.id_pago)
        return comprobante

    @classmethod
    def obtener_comprobante(cls, *, id_comprobante: int, tenant_id: int) -> ComprobantePago:
        comprobante = ComprobantePago.objects.filter(id_comprobante=id_comprobante).first()
        if not comprobante:
            raise ValidationError("Comprobante no encontrado.")

        # Si no es un pago global de SaaS (veterinaria_id is Null), validar el tenant
        if comprobante.veterinaria_id is not None and comprobante.veterinaria_id != tenant_id:
            raise PermissionDenied("No tienes acceso a este comprobante.")

        return comprobante

    @classmethod
    def _generar_siguiente_correlativo(cls, *, tenant_id: int | None) -> str:
        prefix = "REC"
        # Bloquear con select_for_update la fila del último comprobante del tenant
        qs = ComprobantePago.objects.select_for_update().filter(veterinaria_id=tenant_id)
        max_num_str = qs.aggregate(Max("numero_comprobante"))["numero_comprobante__max"]

        if not max_num_str:
            return f"{prefix}-000001"

        try:
            # Formato esperado: REC-000001
            parts = max_num_str.split("-")
            if len(parts) == 2:
                next_val = int(parts[1]) + 1
            else:
                next_val = 1
        except Exception:
            next_val = 1

        return f"{prefix}-{next_val:06d}"

    @classmethod
    def _construir_detalle_items(cls, *, pago: Pago) -> dict:
        items = []
        tipo = pago.tipo_referencia
        ref_id = pago.referencia_id

        if tipo == Pago.TipoReferencia.VENTA_WEB:
            venta = Venta.objects.filter(id_venta=ref_id).first()
            if venta:
                for det in venta.detalles.filter(estado=True):
                    items.append({
                        "id": det.id_detalle_venta,
                        "tipo": det.tipo_item,
                        "descripcion": det.descripcion_item,
                        "cantidad": float(det.cantidad),
                        "precio_unitario": float(det.precio_unitario),
                        "subtotal": float(det.subtotal)
                    })
        elif tipo == Pago.TipoReferencia.PEDIDO_MOVIL:
            pedido = Pedido.objects.filter(id_pedido=ref_id).first()
            if pedido:
                for det in pedido.detalles.filter(estado=True):
                    items.append({
                        "id": det.id_detalle_pedido,
                        "tipo": "PRODUCTO",
                        "descripcion": det.producto.nombre,
                        "cantidad": float(det.cantidad),
                        "precio_unitario": float(det.precio_unitario),
                        "subtotal": float(det.subtotal)
                    })
        elif tipo == Pago.TipoReferencia.CITA_SERVICIO:
            cita = Cita.objects.filter(id_cita=ref_id).first()
            if cita:
                items.append({
                    "id": cita.id_cita,
                    "tipo": "SERVICIO",
                    "descripcion": f"Cita de servicio: {cita.servicio.nombre} ({cita.get_modalidad_display()})",
                    "cantidad": 1.0,
                    "precio_unitario": float(cita.precio_servicio.precio),
                    "subtotal": float(cita.precio_servicio.precio)
                })
        elif tipo == Pago.TipoReferencia.SAAS_SUSCRIPCION:
            event = BillingDemoEvent.objects.filter(id_billing_demo_event=ref_id).first()
            if event:
                items.append({
                    "id": event.id_billing_demo_event,
                    "tipo": "SAAS",
                    "descripcion": f"Suscripción al Plan SaaS {event.plan.nombre}",
                    "cantidad": 1.0,
                    "precio_unitario": float(event.plan.precio_mensual),
                    "subtotal": float(event.plan.precio_mensual)
                })

        return {
            "referencia_tipo": tipo,
            "referencia_id": ref_id,
            "monto_total": float(pago.monto),
            "moneda": pago.moneda,
            "items": items
        }
