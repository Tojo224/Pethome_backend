from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, F
from ..models import StockPunto, Producto


class InventarioValidacionService:
    """
    Servicio para validar condiciones de inventario y alertas
    """

    @staticmethod
    def get_stocks_bajos(veterinaria_id):
        """
        Obtiene todos los stocks por debajo del mínimo
        """
        return StockPunto.objects.filter(
            veterinaria_id=veterinaria_id,
            cantidad__lte=F("cantidad_minima"),
            cantidad__gt=0,
        ).select_related("producto", "punto_inventario")

    @staticmethod
    def get_stocks_agotados(veterinaria_id):
        """
        Obtiene todos los stocks agotados (cantidad = 0)
        """
        return StockPunto.objects.filter(
            veterinaria_id=veterinaria_id,
            cantidad=0,
        ).select_related("producto", "punto_inventario")

    @staticmethod
    def get_productos_vencidos(veterinaria_id):
        """
        Obtiene todos los productos vencidos
        """
        hoy = timezone.now().date()
        return StockPunto.objects.filter(
            veterinaria_id=veterinaria_id,
            fecha_vencimiento_lote__lt=hoy,
            cantidad__gt=0,
        ).select_related("producto", "punto_inventario")

    @staticmethod
    def get_productos_proximo_vencer(veterinaria_id, dias=30):
        """
        Obtiene productos próximos a vencer dentro de X días
        """
        hoy = timezone.now().date()
        fecha_alerta = hoy + timedelta(days=dias)
        
        return StockPunto.objects.filter(
            veterinaria_id=veterinaria_id,
            fecha_vencimiento_lote__lte=fecha_alerta,
            fecha_vencimiento_lote__gt=hoy,
            cantidad__gt=0,
        ).select_related("producto", "punto_inventario")

    @staticmethod
    def get_alertas_completas(veterinaria_id, dias_alerta=30):
        """
        Obtiene todas las alertas consolidadas: stock bajo, agotado, vencidos y próximos a vencer
        """
        return {
            "stocks_bajos": list(InventarioValidacionService.get_stocks_bajos(veterinaria_id).values(
                "id_stock",
                "producto__nombre",
                "cantidad",
                "cantidad_minima",
                "punto_inventario__nombre",
                "numero_lote",
            )),
            "stocks_agotados": list(InventarioValidacionService.get_stocks_agotados(veterinaria_id).values(
                "id_stock",
                "producto__nombre",
                "punto_inventario__nombre",
                "numero_lote",
            )),
            "productos_vencidos": list(InventarioValidacionService.get_productos_vencidos(veterinaria_id).values(
                "id_stock",
                "producto__nombre",
                "fecha_vencimiento_lote",
                "punto_inventario__nombre",
                "numero_lote",
                "cantidad",
            )),
            "productos_proximo_vencer": list(
                InventarioValidacionService.get_productos_proximo_vencer(veterinaria_id, dias_alerta).values(
                "id_stock",
                "producto__nombre",
                "fecha_vencimiento_lote",
                "punto_inventario__nombre",
                "numero_lote",
                "cantidad",
                "producto__dias_alerta_vencimiento",
            )),
        }

    @staticmethod
    def get_resumen_alertas(veterinaria_id, dias_alerta=30):
        """
        Obtiene un resumen con conteos de alertas
        """
        alertas = InventarioValidacionService.get_alertas_completas(veterinaria_id, dias_alerta)
        
        return {
            "cantidad_stocks_bajos": len(alertas["stocks_bajos"]),
            "cantidad_stocks_agotados": len(alertas["stocks_agotados"]),
            "cantidad_productos_vencidos": len(alertas["productos_vencidos"]),
            "cantidad_productos_proximo_vencer": len(alertas["productos_proximo_vencer"]),
            "total_alertas": (
                len(alertas["stocks_bajos"])
                + len(alertas["stocks_agotados"])
                + len(alertas["productos_vencidos"])
                + len(alertas["productos_proximo_vencer"])
            ),
        }

    @staticmethod
    def validar_producto_disponible(stock_punto_id, cantidad_requerida):
        """
        Valida si un producto está disponible en la cantidad requerida
        y no está vencido
        """
        try:
            stock = StockPunto.objects.get(id_stock=stock_punto_id)
            
            # Verificar si está vencido
            if stock.esta_vencido():
                return False, "El producto está vencido"
            
            # Verificar si hay cantidad suficiente
            if stock.cantidad < cantidad_requerida:
                return False, f"Stock insuficiente. Disponible: {stock.cantidad}"
            
            return True, "Producto disponible"
        except StockPunto.DoesNotExist:
            return False, "Stock no encontrado"

    @staticmethod
    def obtener_productos_para_reposicion(veterinaria_id):
        """
        Obtiene lista de productos que necesitan reposición (stock bajo)
        """
        stocks_bajos = InventarioValidacionService.get_stocks_bajos(veterinaria_id)
        
        resultado = []
        for stock in stocks_bajos:
            cantidad_faltante = stock.cantidad_minima - stock.cantidad
            resultado.append({
                "stock_id": stock.id_stock,
                "producto_id": stock.producto_id,
                "producto_nombre": stock.producto.nombre,
                "punto_inventario": stock.punto_inventario.nombre,
                "cantidad_actual": stock.cantidad,
                "cantidad_minima": stock.cantidad_minima,
                "cantidad_faltante": cantidad_faltante,
                "proveedor": stock.producto.proveedor.nombre if stock.producto.proveedor else "Sin proveedor",
            })
        
        return resultado
