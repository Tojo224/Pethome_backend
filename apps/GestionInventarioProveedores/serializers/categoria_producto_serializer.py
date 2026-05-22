from rest_framework import serializers
from apps.GestionInventarioProveedores.models.categoria_producto import CategoriaProducto


class EstadoField(serializers.Field):
    def to_representation(self, value):
        return "Activo" if value else "Inactivo"

    def to_internal_value(self, data):
        if isinstance(data, bool):
            return data
        if isinstance(data, str):
            v = data.strip().lower()
            if v in ("activo", "true", "1", "si", "sí"):
                return True
            if v in ("inactivo", "false", "0", "no"):
                return False
        raise serializers.ValidationError("Valor de estado inválido")


class CategoriaProductoSerializer(serializers.ModelSerializer):
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)
    estado = EstadoField()

    class Meta:
        model = CategoriaProducto
        fields = [
            "id_categoria_producto",
            "nombre",
            "descripcion",
            "estado",
            "veterinaria",
            "id_veterinaria",
        ]
        read_only_fields = ["id_categoria_producto"]