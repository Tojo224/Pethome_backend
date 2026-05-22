from rest_framework import serializers

from apps.AutenticacionySeguridad.models import Veterinaria
from apps.GestionInventarioProveedores.models import CategoriaProducto, Producto, Proveedor


class EstadoField(serializers.Field):
    def to_representation(self, value):
        return "Activo" if value else "Inactivo"

    def to_internal_value(self, data):
        if isinstance(data, bool):
            return data

        if isinstance(data, str):
            value = data.strip().lower()
            if value in ("activo", "true", "1", "si", "sí"):
                return True
            if value in ("inactivo", "false", "0", "no"):
                return False

        raise serializers.ValidationError("Valor de estado inválido")


class ProductoSerializer(serializers.ModelSerializer):
    id_categoria_producto = serializers.PrimaryKeyRelatedField(
        source="categoria_producto",
        queryset=CategoriaProducto.objects.all(),
    )
    id_proveedor = serializers.PrimaryKeyRelatedField(
        source="proveedor",
        queryset=Proveedor.objects.all(),
        required=False,
        allow_null=True,
    )
    id_veterinaria = serializers.PrimaryKeyRelatedField(
        source="veterinaria",
        queryset=Veterinaria.objects.all(),
        required=False,
    )
    estado = EstadoField()
    categoria_nombre = serializers.CharField(
        source="categoria_producto.nombre",
        read_only=True,
    )
    proveedor_nombre = serializers.CharField(
        source="proveedor.nombre",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Producto
        fields = [
            "id_producto",
            "nombre",
            "descripcion",
            "precio_compra",
            "precio_venta",
            "unidad_medida",
            "imagen",
            "visible_catalogo",
            "estado",
            "tipo_mascota",
            "destacado",
            "novedad_desde",
            "novedad_hasta",
            "tiene_promocion",
            "tipo_descuento",
            "porcentaje_descuento",
            "monto_descuento",
            "precio_promocional",
            "promocion_fecha_inicio",
            "promocion_fecha_fin",
            "categoria_nombre",
            "proveedor_nombre",
            "id_categoria_producto",
            "id_proveedor",
            "id_veterinaria",
        ]
        read_only_fields = ["id_producto"]
