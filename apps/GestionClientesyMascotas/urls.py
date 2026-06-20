"""URLs para Cliente y Mascota."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.cliente_view import ClienteDetailView, ClienteListCreateView, ClienteMeView
from .views.register_cliente_view import RegisterClienteView

from .views.mascota_view import MascotaViewSet
from .views.adopcion_view import AdopcionViewSet
from .views.mascota_perfil_view import (
    MascotaPerfilView,
    MascotaHistorialClinicoView,
    MascotaHistorialServiciosView,
    MascotasMeView,
)
from .views.usuario_view import UsuarioListView
from apps.GestionServiciosyReserva.views.especie_raza_view import (
    EspecieListCreateView,
    RazaListCreateView,
)


app_name = "clientes"

router = DefaultRouter()
router.register(r"mascotas", MascotaViewSet, basename="mascota")
router.register(r"adopciones", AdopcionViewSet, basename="adopcion")

urlpatterns = [
    # CLIENTES
    path("register/", RegisterClienteView.as_view(), name="cliente-register"),
    path("me/", ClienteMeView.as_view(), name="cliente-me"),
    path("clientes/", ClienteListCreateView.as_view(), name="cliente-list-create"),
    path("clientes/<int:pk>/", ClienteDetailView.as_view(), name="cliente-detail"),

    # MASCOTAS
    path("mascotas/me/", MascotasMeView.as_view(), name="mascotas-me"),
    path("mascotas/<int:id_mascota>/perfil/", MascotaPerfilView.as_view(), name="mascota-perfil"),
    path("mascotas/<int:id_mascota>/historial-clinico/", MascotaHistorialClinicoView.as_view(), name="mascota-historial-clinico"),
    path("mascotas/<int:id_mascota>/historial/", MascotaHistorialServiciosView.as_view(), name="mascota-historial-servicios"),
    path("", include(router.urls)),

    # COMPATIBILIDAD MÓVIL (mantenemos rutas legacy tras refactor a GestionServiciosyReserva)
    path("especies/", EspecieListCreateView.as_view(), name="especie-list-compat"),
    path("razas/", RazaListCreateView.as_view(), name="raza-list-compat"),

    # OTROS
    path("usuarios/", UsuarioListView.as_view(), name="usuario-list"),
]
