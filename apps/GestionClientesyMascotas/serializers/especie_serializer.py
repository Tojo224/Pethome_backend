from rest_framework import serializers
from apps.GestionClientesyMascotas.models.especie import Especie


class EspecieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especie
        fields = ["id_especie", "nombre"]