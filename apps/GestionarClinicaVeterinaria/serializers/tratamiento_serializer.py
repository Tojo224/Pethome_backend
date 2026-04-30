from rest_framework import serializers
from apps.GestionarClinicaVeterinaria.models import Tratamiento


class TratamientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tratamiento
        fields = [
            "id_tratamiento",
            "consulta_clinica",
            "tipo",
            "descripcion",
            "fecha_ini",
            "fecha_fin",
            "observacion",
            "estado_tratamiento",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id_tratamiento",
            "fecha_creacion",
            "fecha_actualizacion",
        ]