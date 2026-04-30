from django.urls import path

from apps.GestionInventarioProveedores.views.producto_view import ProductoListView

urlpatterns = [
    path("productos/", ProductoListView.as_view(), name="producto-list"),
]