import logging
from decimal import Decimal

from decouple import config

try:
    import requests  # type: ignore
except ImportError:
    requests = None

try:
    import stripe  # type: ignore
except ImportError:
    stripe = None

logger = logging.getLogger(__name__)


class StripePaymentProvider:
    @staticmethod
    def get_currency() -> str:
        return "bob"

    @staticmethod
    def _configure_http_client() -> None:
        if not stripe or not requests:
            return

        # En algunos entornos locales hay variables HTTP(S)_PROXY rotas
        # que intentan redirigir Stripe a 127.0.0.1:9. Para Checkout
        # necesitamos salir directo a api.stripe.com.
        session = requests.Session()
        session.trust_env = False
        stripe.default_http_client = stripe.RequestsClient(session=session)

    @staticmethod
    def is_enabled() -> bool:
        stripe_secret = config("STRIPE_SECRET_KEY", default="")
        return bool(stripe) and bool(stripe_secret)

    @classmethod
    def create_checkout_session(cls, *, pago, concept: str, origen: str = "WEB") -> dict:
        demo_auto_confirm = config(
            "DEMO_CHECKOUT_AUTO_CONFIRM",
            default=False,
            cast=bool,
        )

        if not cls.is_enabled():
            if demo_auto_confirm:
                return {
                    "session_id": f"cs_demo_{pago.id_pago}",
                    "checkout_url": "https://example.com/pethome-demo-checkout",
                    "mode": "demo",
                }
            raise ValueError("Stripe no esta configurado o el SDK no esta instalado.")

        stripe.api_key = config("STRIPE_SECRET_KEY")
        cls._configure_http_client()
        currency = cls.get_currency()

        amount = Decimal(str(pago.monto or 0))
        amount_cents = int(amount * 100)

        if origen == "MOBILE":
            success_url = f"pethome://payment-success?pago_id={pago.id_pago}&success=true"
            cancel_url = f"pethome://payment-cancel?pago_id={pago.id_pago}&cancel=true"
        else:
            frontend_success_url = config(
                "STRIPE_SUCCESS_URL",
                default="http://localhost:3000/billing/success",
            )
            frontend_cancel_url = config(
                "STRIPE_CANCEL_URL",
                default="http://localhost:3000/billing/cancel",
            )
            success_url = f"{frontend_success_url}?pago_id={pago.id_pago}&success=true"
            cancel_url = f"{frontend_cancel_url}?pago_id={pago.id_pago}&cancel=true"

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
            "mode": "stripe",
        }

    @classmethod
    def retrieve_checkout_session(cls, session_id: str):
        if not cls.is_enabled() or not session_id:
            return None

        stripe.api_key = config("STRIPE_SECRET_KEY")
        cls._configure_http_client()
        return stripe.checkout.Session.retrieve(session_id)
