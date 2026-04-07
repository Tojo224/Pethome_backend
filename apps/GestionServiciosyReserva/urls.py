from django.urls import path
from .views import (
    CategoriaServicioListCreateView,
    CategoriaServicioDetailView,
    ServicioListCreateView,
    ServicioDetailView,
    PrecioServicioListCreateView,
    PrecioServicioDetailView,
)

urlpatterns = [
    # Categorías
    path('categorias-servicio/', CategoriaServicioListCreateView.as_view(), name='categoria-list-create'),
    path('categorias/<int:pk>/', CategoriaServicioDetailView.as_view(), name='categoria-detail'),

    # Servicios
    path('', ServicioListCreateView.as_view(), name='servicio-list-create'),
    path('<int:pk>/', ServicioDetailView.as_view(), name='servicio-detail'),

    # Precios
    path('precios-servicio/', PrecioServicioListCreateView.as_view(), name='precio-list-create'),
    path('precios/<int:pk>/', PrecioServicioDetailView.as_view(), name='precio-detail'),
]