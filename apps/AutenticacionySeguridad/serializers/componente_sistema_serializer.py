from rest_framework import serializers
from ..models import ComponenteSistema

class ComponenteSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponenteSistema
        fields = [
            "id_componente",
            "codigo",
            "nombre",
            "tipo",
            "plataforma",
        ]
