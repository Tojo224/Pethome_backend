from django.urls import path

from apps.GestiondeVentasyPagos.views import (
    CarritoDetalleView,
    CarritoItemCreateView,
    CarritoItemDetailView,
    CarritoVaciarView,
    VentaViewSet,
)

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
]
