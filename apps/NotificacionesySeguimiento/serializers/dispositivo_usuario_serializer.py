from rest_framework import serializers
from apps.NotificacionesySeguimiento.models import DispositivoUsuario

class DispositivoUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispositivoUsuario
        fields = ["token_fcm", "plataforma", "activo"]
        extra_kwargs = {
            "token_fcm": {"required": True},
            "plataforma": {"required": True},
        }

    def create(self, validated_data):
        request = self.context.get("request")
        usuario = request.user
        
        # Un token es único. Si ya existe, lo actualizamos para el usuario actual.
        token = validated_data.get("token_fcm")
        dispositivo, created = DispositivoUsuario.objects.update_or_create(
            token_fcm=token,
            defaults={
                "usuario": usuario,
                "veterinaria": usuario.veterinaria,
                "plataforma": validated_data.get("plataforma"),
                "activo": True
            }
        )
        return dispositivo
