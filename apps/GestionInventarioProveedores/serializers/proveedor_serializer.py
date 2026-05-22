from rest_framework import serializers

from apps.AutenticacionySeguridad.models import Veterinaria
from apps.GestionInventarioProveedores.models.proveedor import Proveedor


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


class ProveedorSerializer(serializers.ModelSerializer):
    veterinaria = serializers.PrimaryKeyRelatedField(queryset=Veterinaria.objects.all(), required=False)
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)
    estado = EstadoField()

    class Meta:
        model = Proveedor
        fields = [
            "id_proveedor",
            "nombre",
            "contacto",
            "telefono",
            "ubicacion",
            "estado",
            "veterinaria",
            "id_veterinaria",
        ]
        read_only_fields = ["id_proveedor", "id_veterinaria"]