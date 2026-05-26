from rest_framework import serializers

from apps.GestionInventarioProveedores.models import PuntoInventario, StockPunto


class PuntoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntoInventario
        fields = ["id_punto", "tipo", "nombre", "descripcion", "estado"]


class StockPuntoSerializer(serializers.ModelSerializer):
    id_punto = serializers.IntegerField(source="punto_inventario_id", read_only=True)
    punto_nombre = serializers.CharField(source="punto_inventario.nombre", read_only=True)
    punto_tipo = serializers.CharField(source="punto_inventario.tipo", read_only=True)
    id_producto = serializers.IntegerField(source="producto_id", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    categoria_producto = serializers.CharField(source="producto.categoria_producto.nombre", read_only=True)
    estado_stock = serializers.SerializerMethodField()

    class Meta:
        model = StockPunto
        fields = [
            "id_stock",
            "id_punto",
            "punto_nombre",
            "punto_tipo",
            "id_producto",
            "producto_nombre",
            "categoria_producto",
            "cantidad",
            "cantidad_minima",
            "estado_stock",
            "fecha_actualizacion",
        ]

    def get_estado_stock(self, obj: StockPunto):
        if obj.cantidad <= 0:
            return "AGOTADO"
        if obj.cantidad <= obj.cantidad_minima:
            return "STOCK_BAJO"
        return "DISPONIBLE"
