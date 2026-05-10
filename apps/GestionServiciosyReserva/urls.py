from django.urls import path, include

from .views import (
    CategoriaServicioDetailView,
    CategoriaServicioDetailLegacyView,
    CategoriaServicioListCreateView,
    CitaDetailView,
    CitaEstadoUpdateView,
    CitaListCreateView,
    PrecioServicioDetailLegacyView,
    PrecioServicioDetailView,
    PrecioServicioListCreateView,
    ServicioDetailView,
    ServicioListCreateView,
)
from .views.agenda_view import DisponibilidadAgendaView, ValidarConflictoView
from .views.especie_raza_view import (
    EspecieListCreateView,
    EspecieDetailView,
    RazaListCreateView,
    RazaDetailView,
)
from .views.precio_servicio_especifico_view import PrecioServicioEspecificoView

urlpatterns = [
    # Categorias
    path("categorias-servicio/", CategoriaServicioListCreateView.as_view(), name="categoria-list-create"),
    path("categorias-servicio/<int:pk>/", CategoriaServicioDetailLegacyView.as_view(), name="categoria-detail-legacy"),
    path("categorias/<int:pk>/", CategoriaServicioDetailView.as_view(), name="categoria-detail"),

    # Servicios
    path("", ServicioListCreateView.as_view(), name="servicio-list-create"),
    path("<int:pk>/", ServicioDetailView.as_view(), name="servicio-detail"),

    # Precios
    path("precios-servicio/", PrecioServicioListCreateView.as_view(), name="precio-list-create"),
    path("precios-servicio/<int:pk>/", PrecioServicioDetailLegacyView.as_view(), name="precio-detail-legacy"),
    path("precios/<int:pk>/", PrecioServicioDetailView.as_view(), name="precio-detail"),

    # Citas
    path("citas/", CitaListCreateView.as_view(), name="cita-list-create"),
    path("citas/<int:pk>/", CitaDetailView.as_view(), name="cita-detail"),
    path("citas/<int:pk>/estado/", CitaEstadoUpdateView.as_view(), name="cita-estado"),
    
    # Agenda y Disponibilidad
    path("agenda/", DisponibilidadAgendaView.as_view(), name="agenda-disponibilidad"),
    path("agenda/validar/", ValidarConflictoView.as_view(), name="agenda-validar"),

    # Especies y Razas
    path("especies/", EspecieListCreateView.as_view(), name="especie-list-create"),
    path("especies/<int:pk>/", EspecieDetailView.as_view(), name="especie-detail"),
    path("razas/", RazaListCreateView.as_view(), name="raza-list-create"),
    path("razas/<int:pk>/", RazaDetailView.as_view(), name="raza-detail"),

    #ChatBot
    path("bot/", include("apps.GestionServiciosyReserva.bot.urls")),

    #Precio de un servicio especifico
    path(
        "precio-servicio-especifico/<int:id_servicio>/",
        PrecioServicioEspecificoView.as_view(),
        name="precio-servicio-especifico",
    ),
]
