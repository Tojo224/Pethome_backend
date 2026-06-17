import json
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from decouple import config

try:
    import stripe  # type: ignore
except ImportError:
    stripe = None

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.GestiondeVentasyPagos.models import Pago, TransaccionPago, ComprobantePago
from apps.GestiondeVentasyPagos.serializers.pagos_serializer import (
    PagoCheckoutSerializer,
    PagoConfirmarManualSerializer,
    PagoReadSerializer,
    ComprobantePagoReadSerializer,
)
from apps.GestiondeVentasyPagos.services.pago_service import PagoService
from apps.GestiondeVentasyPagos.services.comprobante_service import ComprobanteService
from apps.GestiondeVentasyPagos.services.payment_reference_resolver import PaymentReferenceResolver

logger = logging.getLogger(__name__)


class PagoCheckoutSessionView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_id = self.get_tenant_id()
        serializer = PagoCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = PagoService.iniciar_pago_online(
            tipo_referencia=data["tipo_referencia"],
            referencia_id=data["referencia_id"],
            user=request.user,
            tenant_id=tenant_id,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class PagoConfirmarManualView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_id = self.get_tenant_id()
        serializer = PagoConfirmarManualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        pago = PagoService.registrar_pago_manual(
            tipo_referencia=data["tipo_referencia"],
            referencia_id=data["referencia_id"],
            metodo_pago=data["metodo_pago"],
            observacion=data.get("observacion", ""),
            user=request.user,
            tenant_id=tenant_id,
        )
        return Response(PagoReadSerializer(pago).data, status=status.HTTP_200_OK)


class PagoViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PagoReadSerializer

    def get_queryset(self):
        tenant_id = self.get_tenant_id()
        return Pago.objects.filter(veterinaria_id=tenant_id).order_by("-fecha_creacion")


class ComprobantePagoViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ComprobantePagoReadSerializer

    def get_queryset(self):
        tenant_id = self.get_tenant_id()
        return ComprobantePago.objects.filter(veterinaria_id=tenant_id).order_by("-fecha_emision")


@method_decorator(csrf_exempt, name="dispatch")
class StripePaymentsWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        stripe_secret_key = config("STRIPE_SECRET_KEY", default="")
        stripe_payments_webhook_secret = config("STRIPE_PAYMENTS_WEBHOOK_SECRET", default="")

        if not stripe or not stripe_secret_key or not stripe_payments_webhook_secret:
            logger.error("Pasarela Stripe de pagos no está correctamente configurada en el servidor.")
            return Response({"detail": "Pasarela Stripe no configurada."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        stripe.api_key = stripe_secret_key

        try:
            stripe_event = stripe.Webhook.construct_event(payload, sig_header, stripe_payments_webhook_secret)
        except Exception as e:
            logger.warning("Firma de webhook de pagos inválida: %s", str(e))
            return Response({"detail": "Firma de webhook inválida."}, status=status.HTTP_400_BAD_REQUEST)

        event_dict = json.loads(payload.decode("utf-8"))
        event_type = event_dict.get("type")
        event_id = event_dict.get("id")
        obj = event_dict.get("data", {}).get("object", {}) or {}

        obj_type = obj.get("object")
        obj_id = obj.get("id")
        obj_payment_intent = obj.get("payment_intent")
        obj_amount_total = obj.get("amount_total")
        obj_amount = obj.get("amount")
        obj_currency = obj.get("currency")
        obj_metadata = obj.get("metadata") or {}

        # Encontrar pago usando metadatos o session_id o payment_intent
        pago_id = obj_metadata.get("pago_id") or obj.get("client_reference_id")
        pago = None

        if pago_id:
            pago = Pago.objects.select_for_update().filter(id_pago=int(pago_id)).first()
        
        if not pago and obj_type == "checkout.session":
            pago = Pago.objects.select_for_update().filter(stripe_session_id=obj_id).first()

        if not pago:
            payment_intent_id = obj_payment_intent or obj_id
            if payment_intent_id:
                pago = Pago.objects.select_for_update().filter(stripe_payment_intent_id=payment_intent_id).first()

        if not pago:
            logger.warning("Webhook Stripe recibido pero no se encontró un pago coincidente en base de datos. type=%s event_id=%s", event_type, event_id)
            return Response({"detail": "Webhook recibido sin pago asociado."}, status=status.HTTP_200_OK)

        # Idempotencia: si ya fue procesado como PAGADO
        if pago.estado_pago == Pago.EstadoPago.PAGADO:
            logger.info("Webhook recibido para Pago #%d que ya fue procesado como PAGADO.", pago.id_pago)
            return Response({"detail": "Pago ya confirmado anteriormente."}, status=status.HTTP_200_OK)

        # Actualizar datos de Stripe en el Pago
        if obj_type == "checkout.session":
            pago.stripe_session_id = obj_id
            if obj_payment_intent:
                pago.stripe_payment_intent_id = obj_payment_intent
        elif obj_type == "payment_intent":
            pago.stripe_payment_intent_id = obj_id

        # Procesar los tipos de evento
        if event_type in ["checkout.session.completed", "payment_intent.succeeded"]:
            # Evitar confirmaciones duplicadas a nivel de webhook
            PagoService._validar_recurso_pagado(
                tipo_referencia=pago.tipo_referencia,
                referencia_id=pago.referencia_id,
                tenant_id=pago.veterinaria_id
            )
            pago.estado_pago = Pago.EstadoPago.PAGADO
            pago.fecha_confirmacion = timezone.now()
            pago.codigo_transaccion = f"STRIPE-{obj_payment_intent or obj_id}"
            pago.save()

            # Guardar log de transacción exitosa
            TransaccionPago.objects.create(
                pago=pago,
                veterinaria=pago.veterinaria,
                provider="STRIPE",
                provider_reference=obj_id,
                estado="PAGADO",
                monto=pago.monto,
                request_payload=event_dict.get("data", {}),
                response_payload={"status": "confirmed_by_webhook", "event_id": event_id},
                fecha_respuesta=timezone.now()
            )

            # Resolver la aprobación del recurso
            PaymentReferenceResolver.resolve_payment_approval(
                tipo_referencia=pago.tipo_referencia,
                referencia_id=pago.referencia_id,
                tenant_id=pago.veterinaria_id,
                user=pago.usuario
            )

            # Generar comprobante
            ComprobanteService.generar_comprobante(pago=pago)
            logger.info("Pago #%d confirmado y resuelto mediante Stripe Webhook.", pago.id_pago)

        elif event_type in ["payment_intent.payment_failed", "checkout.session.expired"]:
            pago.estado_pago = Pago.EstadoPago.FALLIDO
            pago.save()

            # Guardar log de transacción fallida
            TransaccionPago.objects.create(
                pago=pago,
                veterinaria=pago.veterinaria,
                provider="STRIPE",
                provider_reference=obj_id,
                estado="FALLIDO",
                monto=pago.monto,
                request_payload=event_dict.get("data", {}),
                response_payload={"status": "failed_by_webhook", "event_id": event_id},
                fecha_respuesta=timezone.now()
            )
            logger.warning("Pago #%d marcado como FALLIDO mediante Stripe Webhook.", pago.id_pago)

        return Response({"detail": "Webhook procesado exitosamente."}, status=status.HTTP_200_OK)
