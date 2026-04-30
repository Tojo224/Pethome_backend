from rest_framework import serializers
from apps.GestionarClinicaVeterinaria.models import Receta
from apps.GestionarClinicaVeterinaria.serializers.detalle_receta_serializer import DetalleRecetaSerializer


class RecetaSerializer(serializers.ModelSerializer):
    detalles = DetalleRecetaSerializer(many=True, read_only=True)

    class Meta:
        model = Receta
        fields = [
            "id_receta",
            "consulta_clinica",
            "fecha",
            "indicaciones",
            "observacion",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
            "detalles",
        ]
        read_only_fields = [
            "id_receta",
            "consulta_clinica",
            "fecha_creacion",
            "fecha_actualizacion",
        ]