from rest_framework import serializers
from ..models import CategoriaServicio

class CategoriaServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaServicio
        fields = ["id_categoria", "nombre", "descripcion", "estado"]

    def _tenant_id(self):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        return getattr(tenant, "id", None)

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        tenant_id = self._tenant_id()
        if tenant_id is None:
            raise serializers.ValidationError("No se pudo resolver el tenant activo.")

        queryset = CategoriaServicio.objects.filter(
            nombre__iexact=value,
            veterinaria_id=tenant_id,
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe una categoría con este nombre.")
        return value
    