from django.urls import path

from apps.GestionInventarioProveedores.views.producto_view import (
    ProductoViewSet,
    PublicProductoCatalogoListView,
)
from apps.GestionInventarioProveedores.views.categoria_producto_view import CategoriaProductoViewSet
from apps.GestionInventarioProveedores.views.proveedor_view import ProveedorViewSet
from apps.GestionInventarioProveedores.views.unidad_medida_view import UnidadMedidaListView
from apps.GestionInventarioProveedores.views.inventario_movimiento_view import InventarioMovimientoViewSet
from apps.GestionInventarioProveedores.views.inventario_stock_view import InventarioStockViewSet
from apps.GestionInventarioProveedores.views.punto_inventario_view import PuntoInventarioViewSet

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

movimiento_list = InventarioMovimientoViewSet.as_view({
    "get": "list",
    "post": "create",
})

movimiento_detail = InventarioMovimientoViewSet.as_view({
    "get": "retrieve",
})

stock_general = InventarioStockViewSet.as_view({
    "get": "general",
})

stock_unidades_moviles = InventarioStockViewSet.as_view({
    "get": "unidades_moviles",
})

stock_alertas = InventarioStockViewSet.as_view({
    "get": "alertas",
})

stock_disponibilidad = InventarioStockViewSet.as_view({
    "get": "disponibilidad",
})

punto_inventario_list = PuntoInventarioViewSet.as_view({
    "get": "list",
})

urlpatterns = [
    path("unidades-medida/", UnidadMedidaListView.as_view(), name="unidad-medida-list"),
    path("catalogo-publico/", PublicProductoCatalogoListView, name="catalogo-publico-list"),
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
    path("movimientos/", movimiento_list, name="inventario-movimiento-list"),
    path("movimientos/<int:pk>/", movimiento_detail, name="inventario-movimiento-detail"),
    path("stock/general/", stock_general, name="inventario-stock-general"),
    path("stock/unidades-moviles/", stock_unidades_moviles, name="inventario-stock-unidades-moviles"),
    path("stock/alertas/", stock_alertas, name="inventario-stock-alertas"),
    path("stock/productos/<int:pk>/disponibilidad/", stock_disponibilidad, name="inventario-stock-disponibilidad"),
    path("puntos-inventario/", punto_inventario_list, name="inventario-puntos-list"),
]
