from django.urls import path

from apps.GestionInventarioProveedores.views.producto_view import ProductoViewSet
from apps.GestionInventarioProveedores.views.categoria_producto_view import CategoriaProductoViewSet
from apps.GestionInventarioProveedores.views.proveedor_view import ProveedorViewSet
from apps.GestionInventarioProveedores.views.unidad_medida_view import UnidadMedidaListView

producto_list = ProductoViewSet.as_view({
    "get": "list",
    "post": "create",
})

producto_detail = ProductoViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

categoria_producto_list = CategoriaProductoViewSet.as_view({
    "get": "list",
    "post": "create",
})

categoria_producto_detail = CategoriaProductoViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

proveedor_list = ProveedorViewSet.as_view({
    "get": "list",
    "post": "create",
})

proveedor_detail = ProveedorViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

urlpatterns = [
    path("unidades-medida/", UnidadMedidaListView.as_view(), name="unidad-medida-list"),
    path("productos/", producto_list, name="producto-list"),
    path("productos/<int:pk>/", producto_detail, name="producto-detail"),

    path(
        "categorias-producto/",
        categoria_producto_list,
        name="categoria-producto-list",
    ),
    path(
        "categorias-producto/<int:pk>/",
        categoria_producto_detail,
        name="categoria-producto-detail",
    ),
    path(
        "proveedores/",
        proveedor_list,
        name="proveedor-list",
    ),
    path(
        "proveedores/<int:pk>/",
        proveedor_detail,
        name="proveedor-detail",
    ),
]