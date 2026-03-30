from rest_framework import serializers

from GestionClientesyMascotas.models import User, Rol


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ["id_rol", "nombre", "descripcion"]


class UserSerializer(serializers.ModelSerializer):
    role = RolSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id_usuario",
            "correo",
            "role",
            "is_active",
            "date_joined",
        ]
