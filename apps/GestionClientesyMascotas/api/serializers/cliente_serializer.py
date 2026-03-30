"""Serializers para Cliente."""

from rest_framework import serializers
from apps.GestionClientesyMascotas.models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    """Serializer completo para Cliente con datos del usuario."""
    
    correo = serializers.CharField(source="usuario.correo", read_only=True)
    
    class Meta:
        model = Cliente
        fields = [
            'id_cliente',
            'nombre',
            'apellido',
            'correo',
            'telefono',
            'direccion',
            'ciudad',
            'pais',
            'codigo_postal',
            'activo',
            'fecha_registro',
            'fecha_actualizacion',
        ]
        read_only_fields = ['id_cliente', 'fecha_registro', 'fecha_actualizacion', 'correo']


class ClienteCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear un Cliente."""
    
    class Meta:
        model = Cliente
        fields = [
            'usuario',
            'nombre',
            'apellido',
            'telefono',
            'direccion',
            'ciudad',
            'pais',
            'codigo_postal',
        ]
    
    def validate(self, data):
        """Valida que el usuario no tenga ya un cliente asociado."""
        usuario = data.get('usuario')
        if Cliente.objects.filter(usuario=usuario).exists():
            raise serializers.ValidationError(
                "Este usuario ya tiene un perfil de cliente asociado."
            )
        return data


class ClienteUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar un Cliente."""
    
    class Meta:
        model = Cliente
        fields = [
            'nombre',
            'apellido',
            'telefono',
            'direccion',
            'ciudad',
            'pais',
            'codigo_postal',
            'activo',
        ]
