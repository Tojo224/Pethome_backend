import os

from rest_framework import serializers
from apps.GestionarClinicaVeterinaria.models import ArchivoClinico


class ArchivoClinicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivoClinico
        fields = [
            "id_archivo_clinico",
            "consulta_clinica",
            "nombre_archivo",
            "archivo",
            "tipo_archivo",
            "extension",
            "tamano_bytes",
            "descripcion",
            "fecha_subida",
            "estado",
        ]
        read_only_fields = [
            "id_archivo_clinico",
            "fecha_subida",
            "extension",
            "tamano_bytes",
        ]

    def validate_archivo(self, value):
        if value is None:
            return value

        max_size = 15 * 1024 * 1024  # 15 MB
        if value.size > max_size:
            raise serializers.ValidationError(
                "El archivo no debe superar los 15 MB."
            )

        return value

    def create(self, validated_data):
        archivo = validated_data.get("archivo")

        if archivo:
            nombre = getattr(archivo, "name", "")
            extension = os.path.splitext(nombre)[1].lower().replace(".", "")
            validated_data["extension"] = extension or None
            validated_data["tamano_bytes"] = getattr(archivo, "size", None)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        archivo = validated_data.get("archivo")

        if archivo:
            nombre = getattr(archivo, "name", "")
            extension = os.path.splitext(nombre)[1].lower().replace(".", "")
            validated_data["extension"] = extension or None
            validated_data["tamano_bytes"] = getattr(archivo, "size", None)

        return super().update(instance, validated_data)