from rest_framework import serializers
from ..models import Rol
from ..services.auth_security_service import validate_password_complexity

class RegisterSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    nombre = serializers.CharField(max_length=100)
    telefono = serializers.CharField(max_length=20)
    direccion = serializers.CharField(max_length=255)
    role = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all())

    def validate_password(self, value):
        validate_password_complexity(value, "password")
        return value
