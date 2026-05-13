from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import (
    PedidoDetailView,
    PedidoListView,
    SeguimientoDetailView,
    SeguimientoListView,
)
from .views.dispositivo_view import DispositivoUsuarioViewSet
from .views.notificacion_view import NotificacionViewSet

router = SimpleRouter()
router.register(r"dispositivos", DispositivoUsuarioViewSet, basename="dispositivos")
router.register(r"historial", NotificacionViewSet, basename="notificaciones-historial")

urlpatterns = [
    path("seguimientos/", SeguimientoListView.as_view(), name="seguimiento-list"),
    path("seguimientos/<int:id_seguimiento>/", SeguimientoDetailView.as_view(), name="seguimiento-detail"),
    path("pedidos/", PedidoListView.as_view(), name="pedido-list"),
    path("pedidos/<int:id_pedido>/", PedidoDetailView.as_view(), name="pedido-detail"),
    path("", include(router.urls)),
]
