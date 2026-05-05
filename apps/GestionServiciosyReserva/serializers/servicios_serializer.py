from rest_framework import serializers
from ..models import CategoriaServicio, Servicio



class ServicioSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    def _tenant_id(self):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        return getattr(tenant, "id", None)

    class Meta:
        model = Servicio
        fields = [
            "id_servicio",
            "nombre",
            "descripcion",
            "categoria",
            "categoria_nombre",
            "duracion_estimada",
            "disponible_domicilio",
            "estado",
        ]

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        tenant_id = self._tenant_id()
        if tenant_id is None:
            raise serializers.ValidationError("No se pudo resolver el tenant activo.")

        queryset = Servicio.objects.filter(
            nombre__iexact=value,
            veterinaria_id=tenant_id,
        )
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un servicio con este nombre.")
        return value

    def validate_categoria(self, value):
        tenant_id = self._tenant_id()
        if tenant_id is None:
            raise serializers.ValidationError("No se pudo resolver el tenant activo.")

        if not CategoriaServicio.objects.filter(
            pk=value.pk,
            estado=True,
            veterinaria_id=tenant_id,
        ).exists():
            raise serializers.ValidationError("La categoría seleccionada no es válida o está inactiva.")
        return value
    def validate_duracion_estimada(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("La duración estimada no puede ser negativa.")
        return value

    
