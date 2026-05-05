from ..models.producto import Producto
from ..models.categoria_producto import CategoriaProducto
from ..models.proveedor import Proveedor

class ProductoSelector:
    @staticmethod
    def get_productos_by_tenant(veterinaria_id, solo_activos=False):
        queryset = Producto.objects.filter(veterinaria_id=veterinaria_id).select_related("categoria")
        if solo_activos:
            queryset = queryset.filter(is_active=True)
        return queryset

    @staticmethod
    def get_producto_detail(pk, veterinaria_id):
        return Producto.objects.filter(pk=pk, veterinaria_id=veterinaria_id).select_related("categoria").first()

    @staticmethod
    def get_low_stock_products(veterinaria_id):
        from django.db.models import F
        return Producto.objects.filter(
            veterinaria_id=veterinaria_id,
            stock__lte=F('stock_minimo'),
            is_active=True
        )

class CategoriaProductoSelector:
    @staticmethod
    def get_categorias_by_tenant(veterinaria_id):
        return CategoriaProducto.objects.filter(veterinaria_id=veterinaria_id)

class ProveedorSelector:
    @staticmethod
    def get_proveedores_by_tenant(veterinaria_id, solo_activos=False):
        queryset = Proveedor.objects.filter(veterinaria_id=veterinaria_id)
        if solo_activos:
            queryset = queryset.filter(is_active=True)
        return queryset

    @staticmethod
    def get_proveedor_detail(pk, veterinaria_id):
        return Proveedor.objects.filter(pk=pk, veterinaria_id=veterinaria_id).first()
