from rest_framework import serializers
from ..models import PrecioServicio

class PrecioServicioSerializer(serializers.ModelSerializer):
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True)

    class Meta:
        model = PrecioServicio
        fields = [
            "id_precio",
            "servicio",
            "servicio_nombre",
            "variacion",
            "precio",
            "descripcion",
            "estado",
        ]

    def validate_servicio(self, value):
        if not value.estado:
            raise serializers.ValidationError(
                "No se puede asignar un precio a un servicio inactivo."
            )
        return value

    def validate(self, data):
        servicio = data.get("servicio", self.instance.servicio if self.instance else None)
        variacion = data.get("variacion", self.instance.variacion if self.instance else None)

        if servicio and variacion:
            queryset = PrecioServicio.objects.filter(
                servicio=servicio,
                variacion__iexact=variacion.strip()
            )

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({
                    "variacion": "Ya existe un precio para este servicio con esta variación."
                })
        return data