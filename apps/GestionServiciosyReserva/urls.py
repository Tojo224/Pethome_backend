from django.urls import path

from .views import (
    CategoriaServicioDetailView,
    CategoriaServicioListCreateView,
    CitaDetailView,
    CitaEstadoUpdateView,
    CitaListCreateView,
    PrecioServicioDetailView,
    PrecioServicioListCreateView,
    ServicioDetailView,
    ServicioListCreateView,
)

urlpatterns = [
    # Categorias
    path("categorias-servicio/", CategoriaServicioListCreateView.as_view(), name="categoria-list-create"),
    path("categorias-servicio/<int:pk>/", CategoriaServicioDetailView.as_view(), name="categoria-detail-legacy"),
    path("categorias/<int:pk>/", CategoriaServicioDetailView.as_view(), name="categoria-detail"),

    # Servicios
    path("", ServicioListCreateView.as_view(), name="servicio-list-create"),
    path("<int:pk>/", ServicioDetailView.as_view(), name="servicio-detail"),

    # Precios
    path("precios-servicio/", PrecioServicioListCreateView.as_view(), name="precio-list-create"),
    path("precios-servicio/<int:pk>/", PrecioServicioDetailView.as_view(), name="precio-detail-legacy"),
    path("precios/<int:pk>/", PrecioServicioDetailView.as_view(), name="precio-detail"),

    # Citas
    path("citas/", CitaListCreateView.as_view(), name="cita-list-create"),
    path("citas/<int:pk>/", CitaDetailView.as_view(), name="cita-detail"),
    path("citas/<int:pk>/estado/", CitaEstadoUpdateView.as_view(), name="cita-estado"),
]
