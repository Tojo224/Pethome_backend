from django.db.models import F, Q
from django.utils import timezone
from datetime import timedelta

from ..models.producto import Producto
from ..models.categoria_producto import CategoriaProducto
from ..models.proveedor import Proveedor
from ..models.stock_punto import StockPunto


class ProductoSelector:
    @staticmethod
    def get_productos_by_tenant(veterinaria_id, solo_activos=False):
        queryset = Producto.objects.filter(veterinaria_id=veterinaria_id).select_related("categoria_producto")
        if solo_activos:
            queryset = queryset.filter(estado=True)
        return queryset

    @staticmethod
    def get_producto_detail(pk, veterinaria_id):
        return Producto.objects.filter(pk=pk, veterinaria_id=veterinaria_id).select_related("categoria_producto").first()

    @staticmethod
    def get_productos_con_vencimiento(veterinaria_id):
        """Obtiene productos que requieren control de vencimiento"""
        return Producto.objects.filter(
            veterinaria_id=veterinaria_id,
            requiere_control_vencimiento=True,
            estado=True
        )

    @staticmethod
    def get_productos_vencidos(veterinaria_id):
        """Obtiene productos vencidos"""
        hoy = timezone.now().date()
        return Producto.objects.filter(
            veterinaria_id=veterinaria_id,
            requiere_control_vencimiento=True,
            stocks_por_punto__fecha_vencimiento_lote__lt=hoy,
            stocks_por_punto__cantidad__gt=0,
            estado=True
        ).distinct()

    @staticmethod
    def get_productos_proximo_vencer(veterinaria_id, dias=30):
        """Obtiene productos próximos a vencer en X días"""
        hoy = timezone.now().date()
        fecha_alerta = hoy + timedelta(days=dias)
        
        return Producto.objects.filter(
            veterinaria_id=veterinaria_id,
            requiere_control_vencimiento=True,
            stocks_por_punto__fecha_vencimiento_lote__lte=fecha_alerta,
            stocks_por_punto__fecha_vencimiento_lote__gt=hoy,
            stocks_por_punto__cantidad__gt=0,
            estado=True
        ).distinct()


class CategoriaProductoSelector:
    @staticmethod
    def get_categorias_by_tenant(veterinaria_id):
        return CategoriaProducto.objects.filter(veterinaria_id=veterinaria_id)


class ProveedorSelector:
    @staticmethod
    def get_proveedores_by_tenant(veterinaria_id, solo_activos=False):
        queryset = Proveedor.objects.filter(veterinaria_id=veterinaria_id)
        if solo_activos:
            queryset = queryset.filter(estado=True)
        return queryset

    @staticmethod
    def get_proveedor_detail(pk, veterinaria_id):
        return Proveedor.objects.filter(pk=pk, veterinaria_id=veterinaria_id).first()


class StockPuntoSelector:
    """Selectores para consultas de Stock por Punto"""

    @staticmethod
    def get_stocks_by_punto(punto_inventario_id):
        """Obtiene todos los stocks de un punto de inventario"""
        return StockPunto.objects.filter(
            punto_inventario_id=punto_inventario_id
        ).select_related("producto", "veterinaria")

    @staticmethod
    def get_stocks_by_producto(producto_id, veterinaria_id):
        """Obtiene todos los stocks de un producto en todos los puntos"""
        return StockPunto.objects.filter(
            producto_id=producto_id,
            veterinaria_id=veterinaria_id
        ).select_related("punto_inventario")

    @staticmethod
    def get_stocks_bajos(veterinaria_id):
        """Obtiene stocks por debajo del mínimo"""
        return StockPunto.objects.filter(
            veterinaria_id=veterinaria_id,
            cantidad__lte=F("cantidad_minima"),
            cantidad__gt=0
        ).select_related("producto", "punto_inventario")

    @staticmethod
    def get_stocks_agotados(veterinaria_id):
        """Obtiene stocks agotados"""
        return StockPunto.objects.filter(
            veterinaria_id=veterinaria_id,
            cantidad=0
        ).select_related("producto", "punto_inventario")

    @staticmethod
    def get_lotes_vencidos(veterinaria_id):
        """Obtiene lotes vencidos con stock disponible"""
        hoy = timezone.now().date()
        return StockPunto.objects.filter(
            veterinaria_id=veterinaria_id,
            fecha_vencimiento_lote__lt=hoy,
            cantidad__gt=0
        ).select_related("producto", "punto_inventario")

    @staticmethod
    def get_lotes_proximo_vencer(veterinaria_id, dias=30):
        """Obtiene lotes próximos a vencer"""
        hoy = timezone.now().date()
        fecha_alerta = hoy + timedelta(days=dias)
        
        return StockPunto.objects.filter(
            veterinaria_id=veterinaria_id,
            fecha_vencimiento_lote__lte=fecha_alerta,
            fecha_vencimiento_lote__gt=hoy,
            cantidad__gt=0
        ).select_related("producto", "punto_inventario")

    @staticmethod
    def get_alertas_inventario(veterinaria_id, dias_alerta=30):
        """Obtiene consolidado de todas las alertas de inventario"""
        return {
            "stocks_bajos": StockPuntoSelector.get_stocks_bajos(veterinaria_id),
            "stocks_agotados": StockPuntoSelector.get_stocks_agotados(veterinaria_id),
            "lotes_vencidos": StockPuntoSelector.get_lotes_vencidos(veterinaria_id),
            "lotes_proximo_vencer": StockPuntoSelector.get_lotes_proximo_vencer(veterinaria_id, dias_alerta),
        }

    @staticmethod
    def get_stock_detail(stock_id):
        """Obtiene detalles de un stock específico"""
        return StockPunto.objects.filter(
            id_stock=stock_id
        ).select_related("producto", "punto_inventario", "veterinaria").first()

