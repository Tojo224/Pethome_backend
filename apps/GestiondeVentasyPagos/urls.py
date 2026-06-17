from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.GestiondeVentasyPagos.views import (
    CarritoDetalleView,
    CarritoItemCreateView,
    CarritoItemDetailView,
    CarritoVaciarView,
    VentaViewSet,
)
from apps.GestiondeVentasyPagos.views.pagos_view import (
    PagoCheckoutSessionView,
    PagoConfirmarManualView,
    PagoViewSet,
    ComprobantePagoViewSet,
    StripePaymentsWebhookView,
)

router = DefaultRouter()
router.register(r"pagos", PagoViewSet, basename="pago")
router.register(r"comprobantes", ComprobantePagoViewSet, basename="comprobante")

venta_list = VentaViewSet.as_view({
    "get": "list",
    "post": "create",
})

venta_detail = VentaViewSet.as_view({
    "get": "retrieve",
})

urlpatterns = [
    path("ventas/", venta_list, name="venta-list"),
    path("ventas/<int:pk>/", venta_detail, name="venta-detail"),
    path("carrito/", CarritoDetalleView.as_view(), name="carrito-detail"),
    path("carrito/items/", CarritoItemCreateView.as_view(), name="carrito-item-create"),
    path("carrito/items/<int:detalle_id>/", CarritoItemDetailView.as_view(), name="carrito-item-detail"),
    path("carrito/vaciar/", CarritoVaciarView.as_view(), name="carrito-vaciar"),
    
    # Endpoints de Pagos y Comprobantes (CU-28)
    path("pagos/checkout-session/", PagoCheckoutSessionView.as_view(), name="pago-checkout-session"),
    path("pagos/confirmar-manual/", PagoConfirmarManualView.as_view(), name="pago-confirmar-manual"),
    path("pagos/stripe/webhook/", StripePaymentsWebhookView.as_view(), name="pago-stripe-webhook"),
    path("", include(router.urls)),
]
