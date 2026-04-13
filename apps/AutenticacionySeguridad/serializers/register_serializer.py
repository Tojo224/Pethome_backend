from rest_framework import serializers
from ..models import Rol

class RegisterSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    nombre = serializers.CharField(max_length=100)
    telefono = serializers.CharField(max_length=20)
    direccion = serializers.CharField(max_length=255)
    role = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all())