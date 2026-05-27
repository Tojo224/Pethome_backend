from django.urls import path

from apps.GestiondeVentasyPagos.views import VentaViewSet

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
]
