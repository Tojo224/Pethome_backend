from rest_framework import serializers
from apps.AutenticacionySeguridad.models.user import User


class VeterinarioOptionSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="perfil.nombre", read_only=True)

    class Meta:
        model = User
        fields = [
            "id_usuario",
            "correo",
            "nombre",
        ]