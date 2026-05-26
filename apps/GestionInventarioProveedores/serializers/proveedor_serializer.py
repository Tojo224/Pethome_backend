from rest_framework import serializers

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
            "id_veterinaria",
        ]
        read_only_fields = ["id_proveedor", "id_veterinaria"]
        validators = []

    def validate_nombre(self, value):
        nombre = (value or "").strip()
        if not nombre:
            raise serializers.ValidationError("El nombre es requerido")

        request = self.context.get("request")
        tenant_id = None
        if request is not None:
            tenant = getattr(request, "tenant", None)
            tenant_id = getattr(tenant, "id", None) or getattr(request.user, "veterinaria_id", None)

        if tenant_id:
            queryset = Proveedor.objects.filter(veterinaria_id=tenant_id, nombre__iexact=nombre)
            if self.instance is not None:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    "Ya existe un proveedor con ese nombre en esta veterinaria."
                )

        return nombre
