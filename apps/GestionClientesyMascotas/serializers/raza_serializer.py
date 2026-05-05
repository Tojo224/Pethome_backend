from rest_framework import serializers
from apps.GestionClientesyMascotas.models.raza import Raza
from apps.GestionClientesyMascotas.models.especie import Especie


class EspecieMiniRazaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especie
        fields = ["id_especie", "nombre"]


class RazaSerializer(serializers.ModelSerializer):
    especie = EspecieMiniRazaSerializer(read_only=True)

    class Meta:
        model = Raza
        fields = [
            "id_raza",
            "nombre",
            "especie",
        ]