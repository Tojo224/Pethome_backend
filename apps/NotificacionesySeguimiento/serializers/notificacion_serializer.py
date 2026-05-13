from rest_framework import serializers
from apps.NotificacionesySeguimiento.models import Notificacion

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = [
            "id_notificacion", 
            "titulo", 
            "mensaje", 
            "tipo", 
            "estado", 
            "id_entidad_relacionada", 
            "fecha_creacion", 
            "fecha_leida"
        ]
        read_only_fields = ["fecha_creacion"]
