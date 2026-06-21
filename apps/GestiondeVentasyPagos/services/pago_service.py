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
from apps.GestiondeVentasyPagos.services.carrito_service import CarritoService

logger = logging.getLogger(__name__)


class PagoService:
    @classmethod
    @transaction.atomic
    def sincronizar_pago_stripe_pendiente(cls, *, pago: Pago, user=None) -> Pago:
        if not pago or pago.estado_pago == Pago.EstadoPago.PAGADO:
            return pago

        session_id = getattr(pago, "stripe_session_id", None)
        if not session_id or not StripePaymentProvider.is_enabled():
            return pago

        try:
            session = StripePaymentProvider.retrieve_checkout_session(session_id)
        except Exception:
            logger.exception(
                "No se pudo consultar el estado de Stripe para Pago #%s",
                getattr(pago, "id_pago", None),
            )
            return pago

        if not session:
            return pago

        payment_status = getattr(session, "payment_status", None)
        session_status = getattr(session, "status", None)
        payment_intent = getattr(session, "payment_intent", None)

        if payment_intent and pago.stripe_payment_intent_id != payment_intent:
            pago.stripe_payment_intent_id = payment_intent

        if payment_status == "paid":
            if not Pago.objects.filter(
                veterinaria_id=pago.veterinaria_id,
                tipo_referencia=pago.tipo_referencia,
                referencia_id=pago.referencia_id,
                estado_pago=Pago.EstadoPago.PAGADO,
            ).exclude(id_pago=pago.id_pago).exists():
                pago.estado_pago = Pago.EstadoPago.PAGADO
                pago.fecha_confirmacion = timezone.now()
                pago.codigo_transaccion = f"STRIPE-{payment_intent or session_id}"
                pago.save(
                    update_fields=[
                        "stripe_payment_intent_id",
                        "estado_pago",
                        "fecha_confirmacion",
                        "codigo_transaccion",
                    ]
                )

                if not TransaccionPago.objects.filter(
                    pago=pago,
                    provider="STRIPE",
                    estado="PAGADO",
                ).exists():
                    TransaccionPago.objects.create(
                        pago=pago,
                        veterinaria_id=pago.veterinaria_id,
                        provider="STRIPE",
                        provider_reference=session_id,
                        estado="PAGADO",
                        monto=pago.monto,
                        request_payload={"source": "stripe-session-sync"},
                        response_payload={
                            "status": "confirmed_by_session_polling",
                            "session_id": session_id,
                            "payment_intent": payment_intent,
                        },
                        fecha_respuesta=timezone.now(),
                    )

                PaymentReferenceResolver.resolve_payment_approval(
                    tipo_referencia=pago.tipo_referencia,
                    referencia_id=pago.referencia_id,
                    tenant_id=pago.veterinaria_id,
                    user=user or pago.usuario,
                )
                ComprobanteService.generar_comprobante(pago=pago)
            return pago

        if session_status == "expired":
            pago.estado_pago = Pago.EstadoPago.FALLIDO
            pago.save(update_fields=["stripe_payment_intent_id", "estado_pago"])

        elif payment_intent:
            pago.save(update_fields=["stripe_payment_intent_id"])

        return pago

    @classmethod
    @transaction.atomic
    def iniciar_pago_online(cls, *, tipo_referencia: str, referencia_id: int, user, tenant_id: int, origen: str = "WEB") -> dict:
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
            pago.moneda = StripePaymentProvider.get_currency().upper()
            pago.usuario = user
            pago.save(update_fields=["metodo_pago", "monto", "moneda", "usuario"])
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
                moneda=StripePaymentProvider.get_currency().upper(),
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
            session_data = StripePaymentProvider.create_checkout_session(pago=pago, concept=concept, origen=origen)
            pago.stripe_session_id = session_data["session_id"]
            pago.save(update_fields=["stripe_session_id"])
            
            from decouple import config as env_config
            import sys
            
            is_testing = 'test' in sys.argv or any('test' in arg for arg in sys.argv)
            if is_testing:
                demo_auto_confirm = False
            else:
                demo_auto_confirm = env_config(
                    "DEMO_CHECKOUT_AUTO_CONFIRM",
                    default=False,
                    cast=bool,
                )

            # Registrar Intento de Transacción
            TransaccionPago.objects.create(
                pago=pago,
                veterinaria_id=tenant_id,
                provider="STRIPE",
                provider_reference=session_data["session_id"],
                estado="PAGADO" if demo_auto_confirm else "PENDIENTE",
                monto=monto,
                request_payload=tx_req,
                response_payload=session_data
            )

            # NOTA TEMPORAL SPRINT DEMO: Este flujo simula la confirmación inmediata para la presentación.
            # Debe ser retirado o desactivado cuando se termine de implementar/arreglar el webhook real con Stripe.
            if demo_auto_confirm:
                print('[DemoPayment] Confirmando pago automáticamente para presentación')
                pago.estado_pago = Pago.EstadoPago.PAGADO
                pago.fecha_confirmacion = timezone.now()
                pago.codigo_transaccion = f"STRIPE-DEMO-{secrets.token_hex(6).upper()}"
                pago.observacion = "Pago confirmado en modo demo para presentación Sprint"
                pago.save()
                print('[DemoPayment] Pago marcado como PAGADO')

                # Resolver la aprobación del recurso
                PaymentReferenceResolver.resolve_payment_approval(
                    tipo_referencia=pago.tipo_referencia,
                    referencia_id=pago.referencia_id,
                    tenant_id=tenant_id,
                    user=user
                )
                print('[DemoPayment] Pedido/Cita marcado como CONFIRMADO e inventario actualizado')

                # Generar comprobante
                ComprobanteService.generar_comprobante(pago=pago)
                print('[DemoPayment] Comprobante generado')
            
            return {
                "pago_id": pago.id_pago,
                "estado_pago": pago.estado_pago,
                "checkout_url": session_data["checkout_url"],
                "auto_confirmed": demo_auto_confirm
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
