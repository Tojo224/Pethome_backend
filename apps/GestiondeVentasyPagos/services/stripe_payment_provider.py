import logging
from decimal import Decimal
from django.conf import settings
from decouple import config

try:
    import stripe  # type: ignore
except ImportError:
    stripe = None

logger = logging.getLogger(__name__)


class StripePaymentProvider:
    @staticmethod
    def is_enabled() -> bool:
        stripe_secret = config("STRIPE_SECRET_KEY", default="")
        return bool(stripe) and bool(stripe_secret)

    @classmethod
    def create_checkout_session(cls, *, pago, concept: str, origen: str = "WEB") -> dict:
        if not cls.is_enabled():
            raise ValueError("Stripe no está configurado o el SDK no está instalado.")

        stripe.api_key = config("STRIPE_SECRET_KEY")
        currency = (config("STRIPE_CURRENCY", default="usd") or "usd").lower()

        amount = Decimal(str(pago.monto or 0))
        amount_cents = int(amount * 100)

        if origen == "MOBILE":
            success_url = f"pethome://payment-success?pago_id={pago.id_pago}&success=true"
            cancel_url = f"pethome://payment-cancel?pago_id={pago.id_pago}&cancel=true"
        else:
            frontend_success_url = config("STRIPE_SUCCESS_URL", default="http://localhost:3000/billing/success")
            frontend_cancel_url = config("STRIPE_CANCEL_URL", default="http://localhost:3000/billing/cancel")
            success_url = f"{frontend_success_url}?pago_id={pago.id_pago}&success=true"
            cancel_url = f"{frontend_cancel_url}?pago_id={pago.id_pago}&cancel=true"

        # Resolver el id de veterinaria (o None para SaaS global)
        tenant_id = pago.veterinaria_id if pago.veterinaria else None

        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(pago.id_pago),
            metadata={
                "pago_id": str(pago.id_pago),
                "tipo_referencia": pago.tipo_referencia,
                "referencia_id": str(pago.referencia_id),
                "tenant_id": str(tenant_id) if tenant_id else "",
            },
            payment_intent_data={
                "metadata": {
                    "pago_id": str(pago.id_pago),
                    "tipo_referencia": pago.tipo_referencia,
                    "referencia_id": str(pago.referencia_id),
                }
            },
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": concept,
                            "description": f"Pago de {pago.get_tipo_referencia_display()}",
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
        )

        return {
            "session_id": session.id,
            "checkout_url": getattr(session, "url", None),
        }
