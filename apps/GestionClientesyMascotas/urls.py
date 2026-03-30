"""URLs para Cliente."""

from django.urls import path
from apps.GestionClientesyMascotas.views.cliente_view import (
    ClienteListCreateView,
    ClienteDetailView,
    ClienteToggleActivoView,
    ClientePorUsuarioView,
)

app_name = 'clientes'

urlpatterns = [
    # CRUD básico
    path('', ClienteListCreateView.as_view(), name='cliente-list-create'),
    path('<int:cliente_id>/', ClienteDetailView.as_view(), name='cliente-detail'),
    
    # Acciones especiales
    path('<int:cliente_id>/toggle-activo/', ClienteToggleActivoView.as_view(), name='cliente-toggle-activo'),
    path('usuario/<int:usuario_id>/', ClientePorUsuarioView.as_view(), name='cliente-por-usuario'),
]
