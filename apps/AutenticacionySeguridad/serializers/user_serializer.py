from rest_framework import serializers
from ..models import User
from ..serializers.rol_serializer import RolSerializer


class UserSerializer(serializers.ModelSerializer):
    rol = RolSerializer(source="role", read_only=True)

    class Meta:
        model = User
        fields = [
            "id_usuario",
            "correo",
            "rol",
            "is_active",
            "date_joined",
        ]
