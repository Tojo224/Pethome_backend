from rest_framework import serializers
from typing import Any, Optional

from ..models.bitacora import Bitacora


class BitacoraSerializer(serializers.ModelSerializer):
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)
    id_usuario = serializers.SerializerMethodField()
    nombre_usuario = serializers.SerializerMethodField()
    correo_usuario = serializers.SerializerMethodField()
    accion = serializers.SerializerMethodField()
    modulo = serializers.SerializerMethodField()
    descripcion = serializers.SerializerMethodField()
    ip = serializers.SerializerMethodField()
    user_agent = serializers.SerializerMethodField()
    resultado = serializers.SerializerMethodField()
    entidad_tipo = serializers.SerializerMethodField()
    entidad_id = serializers.SerializerMethodField()
    metadatos = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()
    method = serializers.SerializerMethodField()

    class Meta:
        model = Bitacora
        fields = [
            "id_bitacora",
            "id_veterinaria",
            "fecha_hora",
            "id_usuario",
            "nombre_usuario",
            "correo_usuario",
            "accion",
            "modulo",
            "descripcion",
            "ip",
            "user_agent",
            "resultado",
            "entidad_tipo",
            "entidad_id",
            "metadatos",
            "path",
            "method",
        ]
        read_only_fields = fields

    def _payload_value(self, obj, key: str, default: Any = "") -> Any:
        payload = getattr(obj, "payload", None)
        if isinstance(payload, dict):
            return payload.get(key, default)
        return default

    def get_id_usuario(self, obj) -> Optional[int]:
        return self._payload_value(obj, "id_usuario")

    def get_nombre_usuario(self, obj) -> str:
        return self._payload_value(obj, "nombre_usuario", "")

    def get_correo_usuario(self, obj) -> str:
        return self._payload_value(obj, "correo_usuario", "")

    def get_accion(self, obj) -> str:
        return self._payload_value(obj, "accion", "")

    def get_modulo(self, obj) -> str:
        return self._payload_value(obj, "modulo", "")

    def get_descripcion(self, obj) -> str:
        return self._payload_value(obj, "descripcion", "")

    def get_ip(self, obj) -> str:
        return self._payload_value(obj, "ip", "")

    def get_user_agent(self, obj) -> str:
        return self._payload_value(obj, "user_agent", "")

    def get_resultado(self, obj) -> str:
        return self._payload_value(obj, "resultado", "")

    def get_entidad_tipo(self, obj) -> str:
        return self._payload_value(obj, "entidad_tipo", "")

    def get_entidad_id(self, obj) -> str:
        return self._payload_value(obj, "entidad_id", "")

    def get_metadatos(self, obj) -> Any:
        return self._payload_value(obj, "metadatos", {})

    def get_path(self, obj) -> str:
        return self._payload_value(obj, "path", "")

    def get_method(self, obj) -> str:
        return self._payload_value(obj, "method", "")
