from rest_framework import serializers
from ..models.especie import Especie
from ..models.raza import Raza

class EspecieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especie
        fields = ["id_especie", "nombre"]

class RazaSerializer(serializers.ModelSerializer):
    especie_nombre = serializers.ReadOnlyField(source="especie.nombre")
    
    class Meta:
        model = Raza
        fields = ["id_raza", "nombre", "especie", "especie_nombre"]
