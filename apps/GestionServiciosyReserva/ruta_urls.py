from django.urls import path

from .views import (
    DetalleRutaDetailView,
    MisRutasHoyView,
    MisRutasListView,
    RutaProgramadaDetailView,
    RutaProgramadaDetalleListCreateView,
    RutaProgramadaListCreateView,
    UnidadMovilDetailView,
    UnidadMovilListCreateView,
)


urlpatterns = [
    path("unidades-moviles/", UnidadMovilListCreateView.as_view(), name="unidad-movil-list"),
    path("unidades-moviles/<int:pk>/", UnidadMovilDetailView.as_view(), name="unidad-movil-detail"),
    path("rutas-programadas/", RutaProgramadaListCreateView.as_view(), name="ruta-programada-list"),
    path("rutas-programadas/<int:pk>/", RutaProgramadaDetailView.as_view(), name="ruta-programada-detail"),
    path(
        "rutas-programadas/<int:pk>/detalle/",
        RutaProgramadaDetalleListCreateView.as_view(),
        name="ruta-programada-detalle",
    ),
    path("detalle-ruta/<int:pk>/", DetalleRutaDetailView.as_view(), name="detalle-ruta-detail"),
    path("mis-rutas/hoy/", MisRutasHoyView.as_view(), name="mis-rutas-hoy"),
    path("mis-rutas/", MisRutasListView.as_view(), name="mis-rutas"),
]
