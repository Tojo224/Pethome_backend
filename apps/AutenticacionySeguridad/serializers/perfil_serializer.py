from rest_framework import serializers
from ..models import Perfil
from ..services.auth_security_service import validate_password_complexity
from ..services.perfil_service import create_user_with_profile, update_user_with_profile

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
    estado = serializers.BooleanField(write_only=True, required=False)
    is_active = serializers.BooleanField(write_only=True, required=False)
    id_veterinaria = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Perfil
        fields = [
            "correo", 
            "password", 
            "id_rol", 
            "estado",
            "is_active",
            "nombre", 
            "telefono", 
            "direccion",
            "id_veterinaria"
        ]

    def validate_password(self, value):
        validate_password_complexity(value, "password")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        
        # Prioridad: 1. El ID enviado en el body, 2. El ID del tenant actual
        veterinaria_id = validated_data.pop("id_veterinaria", None)
        if not veterinaria_id:
            veterinaria_id = getattr(tenant, "id", None)

        estado = validated_data.pop("estado", None)
        is_active = validated_data.pop("is_active", None)
        if estado is None:
            estado = is_active

        return create_user_with_profile(
            correo=validated_data["correo"],
            password=validated_data["password"],
            id_rol=validated_data["id_rol"],
            nombre=validated_data["nombre"],
            telefono=validated_data["telefono"],
            direccion=validated_data["direccion"],
            estado=estado,
            veterinaria_id=veterinaria_id,
            request_user=request.user if request else None,
        )
    

class PerfilUpdateSerializer(serializers.ModelSerializer):
    correo = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    id_rol = serializers.IntegerField(write_only=True, required=False)
    estado = serializers.BooleanField(required=False)

    class Meta:
        model = Perfil
        fields = [
            "correo",
            "password",
            "id_rol",
            "estado",
            "nombre",
            "telefono",
            "direccion",
        ]

    def validate_password(self, value):
        validate_password_complexity(value, "password")
        return value
    
    def update(self, instance, validated_data):
        return update_user_with_profile(
            perfil=instance,
            correo=validated_data.get("correo"),
            password=validated_data.get("password"),
            id_rol=validated_data.get("id_rol"),
            estado=validated_data.get("estado"),
            nombre=validated_data.get("nombre"),
            telefono=validated_data.get("telefono"),
            direccion=validated_data.get("direccion"),
        )
