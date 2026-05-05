from typing import Optional

from rest_framework import serializers

from apps.GestionarClinicaVeterinaria.models import HistorialClinico
from apps.GestionarClinicaVeterinaria.serializers.consulta_clinica_serializer import (
    ConsultaClinicaSerializer,
)


class HistorialClinicoSerializer(serializers.ModelSerializer):
    mascota_id = serializers.IntegerField(source="mascota.id_mascota", read_only=True)
    mascota_nombre = serializers.CharField(source="mascota.nombre", read_only=True)
    mascota_especie = serializers.CharField(source="mascota.especie.nombre", read_only=True)
    mascota_raza = serializers.SerializerMethodField()
    propietario_id = serializers.IntegerField(source="mascota.usuario.id_usuario", read_only=True)
    propietario_nombre = serializers.CharField(source="mascota.usuario.perfil.nombre", read_only=True)

    consultas_clinicas = ConsultaClinicaSerializer(many=True, read_only=True)

    class Meta:
        model = HistorialClinico
        fields = [
            "id_historial_clinico",
            "mascota",
            "mascota_id",
            "mascota_nombre",
            "mascota_especie",
            "mascota_raza",
            "propietario_id",
            "propietario_nombre",
            "observaciones_generales",
            "fecha_creacion",
            "fecha_actualizacion",
            "estado",
            "consultas_clinicas",
        ]
        read_only_fields = [
            "id_historial_clinico",
            "mascota_id",
            "mascota_nombre",
            "mascota_especie",
            "mascota_raza",
            "propietario_id",
            "propietario_nombre",
            "fecha_creacion",
            "fecha_actualizacion",
            "consultas_clinicas",
        ]

    def get_mascota_raza(self, obj) -> Optional[str]:
        if obj.mascota and obj.mascota.raza:
            return obj.mascota.raza.nombre
        return None

    def validate_mascota(self, value):
        existe = HistorialClinico.objects.filter(mascota=value, estado=True).exists()

        if self.instance:
            existe = HistorialClinico.objects.filter(
                mascota=value,
                estado=True
            ).exclude(pk=self.instance.pk).exists()

        if existe:
            raise serializers.ValidationError(
                "Esta mascota ya tiene un historial clínico activo."
            )

        return value