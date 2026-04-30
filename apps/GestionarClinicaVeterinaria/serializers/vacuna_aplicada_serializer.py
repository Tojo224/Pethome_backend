from rest_framework import serializers
from apps.GestionarClinicaVeterinaria.models import VacunaAplicada


class VacunaAplicadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacunaAplicada
        fields = [
            "id_vacuna_aplicada",
            "consulta_clinica",
            "nombre_vacuna",
            "dosis",
            "fecha_aplicada",
            "fecha_proxima",
            "observacion",
            "lote",
            "fabricante",
            "estado_vacuna",
            "estado",
            "fecha_creacion",
        ]
        read_only_fields = ["id_vacuna_aplicada", "fecha_creacion"]