import logging
import secrets
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.GestiondeVentasyPagos.models import Pago, TransaccionPago, Venta
from apps.NotificacionesySeguimiento.models import Pedido
from apps.GestionServiciosyReserva.models import Cita
from apps.AutenticacionySeguridad.models import BillingDemoEvent
from apps.GestiondeVentasyPagos.services.stripe_payment_provider import StripePaymentProvider
from apps.GestiondeVentasyPagos.services.payment_reference_resolver import PaymentReferenceResolver
from apps.GestiondeVentasyPagos.services.comprobante_service import ComprobanteService

logger = logging.getLogger(__name__)


class PagoService:
    @classmethod
    @transaction.atomic
    def iniciar_pago_online(cls, *, tipo_referencia: str, referencia_id: int, user, tenant_id: int) -> dict:
        """
        Inicializa un pago en línea (Stripe Checkout Session).
        """
        # 1. Validaciones e Idempotencia
        cls._validar_recurso_pagado(tipo_referencia=tipo_referencia, referencia_id=referencia_id, tenant_id=tenant_id)
        
        # Validar stock antes de crear sesión de Stripe para PEDIDO_MOVIL
        if tipo_referencia == Pago.TipoReferencia.PEDIDO_MOVIL:
            pedido = Pedido.objects.filter(id_pedido=referencia_id, veterinaria_id=tenant_id).first()
            if not pedido:
                raise ValidationError("Pedido no encontrado.")
            tiene_stock, msg = PaymentReferenceResolver._validar_stock_pedido(pedido=pedido, tenant_id=tenant_id)
            if not tiene_stock:
                raise ValidationError(f"No se puede iniciar el pago: {msg}")
        
        # Calcular el monto
        monto = cls._calcular_monto(tipo_referencia=tipo_referencia, referencia_id=referencia_id, tenant_id=tenant_id)

        # Si ya existe un pago PENDIENTE o EN_PROCESO para este recurso, lo reutilizamos
        pago = Pago.objects.filter(
            veterinaria_id=tenant_id,
            tipo_referencia=tipo_referencia,
            referencia_id=referencia_id,
            estado_pago__in=[Pago.EstadoPago.PENDIENTE, Pago.EstadoPago.EN_PROCESO]
        ).first()

        if pago:
            pago.metodo_pago = Pago.MetodoPago.STRIPE
            pago.monto = monto
            pago.usuario = user
            pago.save(update_fields=["metodo_pago", "monto", "usuario"])
        else:
            codigo = f"TRX-{secrets.token_hex(6).upper()}"
            pago = Pago.objects.create(
                veterinaria_id=tenant_id,
                usuario=user,
                cliente=user if tipo_referencia == Pago.TipoReferencia.PEDIDO_MOVIL else None,
                tipo_referencia=tipo_referencia,
                referencia_id=referencia_id,
                metodo_pago=Pago.MetodoPago.STRIPE,
                estado_pago=Pago.EstadoPago.PENDIENTE,
                monto=monto,
                codigo_transaccion=codigo,
            )

        # 2. Generar sesión en Stripe
        concept = f"Pago {tipo_referencia} #{referencia_id}"
        
        tx_req = {
            "pago_id": pago.id_pago,
            "concept": concept,
            "monto": str(monto)
        }
        
        try:
            session_data = StripePaymentProvider.create_checkout_session(pago=pago, concept=concept)
            pago.stripe_session_id = session_data["session_id"]
            pago.save(update_fields=["stripe_session_id"])
            
            # Registrar Intento de Transacción
            TransaccionPago.objects.create(
                pago=pago,
                veterinaria_id=tenant_id,
                provider="STRIPE",
                provider_reference=session_data["session_id"],
                estado="PENDIENTE",
                monto=monto,
                request_payload=tx_req,
                response_payload=session_data
            )
            
            return {
                "pago_id": pago.id_pago,
                "estado_pago": pago.estado_pago,
                "checkout_url": session_data["checkout_url"]
            }
        except Exception as e:
            logger.exception("Error al crear sesión de Stripe para Pago #%d", pago.id_pago)
            # Log de transacción fallida
            TransaccionPago.objects.create(
                pago=pago,
                veterinaria_id=tenant_id,
                provider="STRIPE",
                estado="FALLIDO",
                monto=monto,
                request_payload=tx_req,
                response_payload={"error": str(e)}
            )
            raise ValidationError(f"Error al iniciar el pago con Stripe: {str(e)}")

    @classmethod
    @transaction.atomic
    def registrar_pago_manual(cls, *, tipo_referencia: str, referencia_id: int, metodo_pago: str, observacion: str, user, tenant_id: int) -> Pago:
        """
        Registra un pago manual en caja (Efectivo/Transferencia/QR/Administrativo).
        El pago se confirma inmediatamente como PAGADO.
        """
        if metodo_pago == Pago.MetodoPago.STRIPE:
            raise ValidationError("Para pagos en línea debe utilizar la pasarela correspondiente.")

        # 1. Validaciones e Idempotencia
        cls._validar_recurso_pagado(tipo_referencia=tipo_referencia, referencia_id=referencia_id, tenant_id=tenant_id)
        
        monto = cls._calcular_monto(tipo_referencia=tipo_referencia, referencia_id=referencia_id, tenant_id=tenant_id)

        # Si ya existe un pago PENDIENTE o EN_PROCESO, podemos actualizarlo y confirmarlo
        pago = Pago.objects.filter(
            veterinaria_id=tenant_id,
            tipo_referencia=tipo_referencia,
            referencia_id=referencia_id,
            estado_pago__in=[Pago.EstadoPago.PENDIENTE, Pago.EstadoPago.EN_PROCESO]
        ).first()

        codigo = f"TRX-{secrets.token_hex(6).upper()}"
        if pago:
            pago.metodo_pago = metodo_pago
            pago.estado_pago = Pago.EstadoPago.PAGADO
            pago.monto = monto
            pago.usuario = user
            pago.codigo_transaccion = codigo
            pago.observacion = observacion
            pago.fecha_confirmacion = timezone.now()
            pago.save()
        else:
            pago = Pago.objects.create(
                veterinaria_id=tenant_id,
                usuario=user,
                tipo_referencia=tipo_referencia,
                referencia_id=referencia_id,
                metodo_pago=metodo_pago,
                estado_pago=Pago.EstadoPago.PAGADO,
                monto=monto,
                codigo_transaccion=codigo,
                observacion=observacion,
                fecha_confirmacion=timezone.now(),
            )

        # Registrar Transacción Manual
        TransaccionPago.objects.create(
            pago=pago,
            veterinaria_id=tenant_id,
            provider="MANUAL",
            provider_reference=codigo,
            estado="PAGADO",
            monto=monto,
            request_payload={"metodo_pago": metodo_pago, "observacion": observacion},
            response_payload={"status": "confirmed_locally"},
            fecha_respuesta=timezone.now()
        )

        # Actualizar la entidad de negocio referenciada
        PaymentReferenceResolver.resolve_payment_approval(
            tipo_referencia=tipo_referencia,
            referencia_id=referencia_id,
            tenant_id=tenant_id,
            user=user
        )

        # Generar comprobante correlativo
        ComprobanteService.generar_comprobante(pago=pago)

        return pago

    @classmethod
    def _validar_recurso_pagado(cls, *, tipo_referencia: str, referencia_id: int, tenant_id: int) -> None:
        pago_existente = Pago.objects.filter(
            veterinaria_id=tenant_id,
            tipo_referencia=tipo_referencia,
            referencia_id=referencia_id,
            estado_pago=Pago.EstadoPago.PAGADO
        ).exists()

        if pago_existente:
            raise ValidationError("Este recurso ya cuenta con un pago aprobado (PAGADO).")

    @classmethod
    def _calcular_monto(cls, *, tipo_referencia: str, referencia_id: int, tenant_id: int) -> Decimal:
        if tipo_referencia == Pago.TipoReferencia.VENTA_WEB:
            venta = Venta.objects.filter(id_venta=referencia_id, veterinaria_id=tenant_id).first()
            if not venta:
                raise ValidationError("Venta no encontrada.")
            return venta.total
        elif tipo_referencia == Pago.TipoReferencia.PEDIDO_MOVIL:
            pedido = Pedido.objects.filter(id_pedido=referencia_id, veterinaria_id=tenant_id).first()
            if not pedido:
                raise ValidationError("Pedido no encontrado.")
            return pedido.total
        elif tipo_referencia == "CITA_SERVICIO":
            cita = Cita.objects.filter(id_cita=referencia_id, veterinaria_id=tenant_id).first()
            if not cita:
                raise ValidationError("Cita no encontrada.")
            return cita.precio_servicio.precio
        elif tipo_referencia == "SAAS_SUSCRIPCION":
            event = BillingDemoEvent.objects.filter(id_billing_demo_event=referencia_id).first()
            if not event:
                raise ValidationError("Evento de suscripción SaaS no encontrado.")
            return event.plan.precio_mensual
        else:
            raise ValidationError(f"Tipo de referencia '{tipo_referencia}' no válido.")
