import unicodedata

from rest_framework import serializers
from ..models import PrecioServicio

class PrecioServicioSerializer(serializers.ModelSerializer):
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True)

    def validate_modalidad(self, value):
        if value is None:
            return value

        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.strip().upper()

        if "DOMICILIO" in normalized:
            return "DOMICILIO"
        if "CONSULTA" in normalized or "CLINICA" in normalized or "EN CLINICA" in normalized:
            return "CLINICA"

        raise serializers.ValidationError("La modalidad debe ser Clínica o Domicilio.")

    def _tenant_id(self):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        return getattr(tenant, "id", None)

    class Meta:
        model = PrecioServicio
        fields = [
            "id_precio",
            "servicio",
            "servicio_nombre",
            "variacion",
            "modalidad",
            "precio",
            "descripcion",
            "estado",
        ]

    def validate_servicio(self, value):
        tenant_id = self._tenant_id()
        if tenant_id is None:
            raise serializers.ValidationError("No se pudo resolver el tenant activo.")

        if value.veterinaria_id != tenant_id:
            raise serializers.ValidationError(
                "El servicio no pertenece a la veterinaria actual."
            )
        if not value.estado:
            raise serializers.ValidationError(
                "No se puede asignar un precio a un servicio inactivo."
            )
        return value

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a cero.")
        return value

    def validate(self, data):
        tenant_id = self._tenant_id()
        if tenant_id is None:
            raise serializers.ValidationError("No se pudo resolver el tenant activo.")

        servicio = data.get("servicio", self.instance.servicio if self.instance else None)
        variacion = data.get("variacion", self.instance.variacion if self.instance else None)
        modalidad = data.get("modalidad", self.instance.modalidad if self.instance else None)

        if servicio and variacion:
            queryset = PrecioServicio.objects.filter(
                servicio=servicio,
                variacion__iexact=variacion.strip(),
                modalidad__iexact=modalidad.strip() if modalidad else modalidad,
                veterinaria_id=tenant_id,
            )

            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({
                    "variacion": "Ya existe un precio para este servicio con esta variación y modalidad."
                })

        return data