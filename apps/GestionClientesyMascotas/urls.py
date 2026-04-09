"""URLs para Cliente."""

from django.urls import path
from .views.cliente_view import ClienteDetailView, ClienteListCreateView, ClienteMeView
from .views.register_cliente_view import RegisterClienteView

app_name = 'clientes'

urlpatterns = [
    path("register/", RegisterClienteView.as_view(), name="cliente-register"),
    path("me/", ClienteMeView.as_view(), name="cliente-me"),
    path('', ClienteListCreateView.as_view(), name='cliente-list-create'),
    path('<int:pk>/', ClienteDetailView.as_view(), name='cliente-detail'),
]
