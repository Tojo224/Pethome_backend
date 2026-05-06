from rest_framework import serializers

class AuthContextSerializer(serializers.Serializer):
    """
    Serializador para la respuesta de contexto SaaS (Usuario, Veterinaria, Plan, Componentes).
    """
    usuario = serializers.DictField()
    veterinaria = serializers.DictField(allow_null=True)
    plan = serializers.DictField(allow_null=True)
    componentes = serializers.ListField(child=serializers.DictField())
