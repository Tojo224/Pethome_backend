from rest_framework import serializers
from django.db import transaction
from ..models import Perfil, User, Rol


class PerfilSerializer(serializers.ModelSerializer):
    correo = serializers.EmailField(source="usuario.correo", read_only=True)
    rol = serializers.CharField(source="usuario.role.nombre", read_only=True)
    estado = serializers.BooleanField(source="usuario.is_active", read_only=True)

    class Meta:
        model = Perfil
        fields = [
            "id_perfil",
            "usuario", 
            "correo",
            "rol",
            "nombre",
            "telefono",
            "direccion",
            "estado",
            "fecha_creacion",
        ]
        read_only_fields = ["id_perfil", "usuario", "fecha_creacion"]

class PerfilCreateSerializer(serializers.ModelSerializer):
    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    id_rol = serializers.IntegerField(write_only=True)

    class Meta:
        model = Perfil
        fields = [
            "correo", 
            "password", 
            "id_rol", 
            "nombre", 
            "telefono", 
            "direccion"
        ]

    def create(self, validated_data):
        # Extraemos los datos del usuario
        correo = validated_data.pop('correo')
        password = validated_data.pop('password')
        id_rol = validated_data.pop('id_rol')
        
        # Usamos una transacción para que si algo falla, no se cree nada
        with transaction.atomic():
            # 1. Buscamos el rol
            rol = Rol.objects.get(pk=id_rol)
            
            # 2. Creamos el usuario (usando create_user para que encripte la clave)
            user = User.objects.create_user(
                correo=correo,
                password=password,
                role=rol
            )
            
            # 3. Creamos el perfil asociado
            perfil = Perfil.objects.create(usuario=user, **validated_data)
            
            return perfil