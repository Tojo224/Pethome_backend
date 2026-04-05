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
    path('categorias-servicio/', CategoriaServicioListCreateView.as_view(), name='categoria-list-create'),
    path('categorias-servicio/<int:pk>/', CategoriaServicioDetailView.as_view(), name='categoria-detail'),

    path('servicios/', ServicioListCreateView.as_view(), name='servicio-list-create'),
    path('servicios/<int:pk>/', ServicioDetailView.as_view(), name='servicio-detail'),

    path('precios-servicio/', PrecioServicioListCreateView.as_view(), name='precio-list-create'),
    path('precios-servicio/<int:pk>/', PrecioServicioDetailView.as_view(), name='precio-detail'),
]