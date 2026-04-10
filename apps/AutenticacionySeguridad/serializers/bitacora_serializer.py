from rest_framework import serializers

from ..models.bitacora import Bitacora


class BitacoraSerializer(serializers.ModelSerializer):
    usuario_id = serializers.IntegerField(source="usuario.id", read_only=True)
    usuario_nombre = serializers.SerializerMethodField()
    accion_display = serializers.CharField(source="get_accion_display", read_only=True)
    resultado_display = serializers.CharField(source="get_resultado_display", read_only=True)
    modulo_display = serializers.CharField(source="get_modulo_display", read_only=True)

    class Meta:
        model = Bitacora
        fields = [
            "id_bitacora",
            "fecha_hora",
            "usuario_id",
            "usuario_nombre",
            "accion",
            "accion_display",
            "descripcion",
            "ip",
            "user_agent",
            "modulo",
            "modulo_display",
            "entidad_tipo",
            "entidad_id",
            "resultado",
            "resultado_display",
            "metadatos",
        ]
        read_only_fields = fields

    def get_usuario_nombre(self, obj):
        if not obj.usuario:
            return "Sistema/Anónimo"

        correo = getattr(obj.usuario, "correo", "")
        if correo:
            return correo

        full_name = ""
        if hasattr(obj.usuario, "get_full_name"):
            full_name = obj.usuario.get_full_name()

        return full_name or getattr(obj.usuario, "username", str(obj.usuario))