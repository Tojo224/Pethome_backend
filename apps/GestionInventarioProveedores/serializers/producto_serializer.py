from rest_framework import serializers
from apps.GestionInventarioProveedores.models import Producto


class ProductoSerializer(serializers.ModelSerializer):
    id_categoria_producto = serializers.IntegerField(
        source="categoria_producto_id",
        read_only=True
    )
    id_proveedor = serializers.IntegerField(
        source="proveedor_id",
        read_only=True
    )

    class Meta:
        model = Producto
        fields = [
            "id_producto",
            "nombre",
            "precio_compra",
            "precio_venta",
            "unidad_medida",
            "estado",
            "categoria_producto",
            "proveedor",
            "id_categoria_producto",
            "id_proveedor",
        ]