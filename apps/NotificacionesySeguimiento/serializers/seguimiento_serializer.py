from rest_framework import serializers

from ..models import Seguimiento
from ..permissions import is_client


class SeguimientoListSerializer(serializers.ModelSerializer):
    usuario = serializers.SerializerMethodField()
    cita = serializers.SerializerMethodField()
    pedido = serializers.SerializerMethodField()

    class Meta:
        model = Seguimiento
        fields = [
            "id_seguimiento",
            "tipo_seguimiento",
            "estado_anterior",
            "estado_actual",
            "descripcion",
            "fecha_hora",
            "visible_cliente",
            "usuario",
            "cita",
            "pedido",
        ]

    def get_usuario(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and is_client(user):
            return None

        user = obj.usuario
        if user is None:
            return None

        perfil = getattr(user, "perfil", None)
        return {
            "id_usuario": user.id_usuario,
            "correo": user.correo,
            "nombre": getattr(perfil, "nombre", None),
        }

    def get_cita(self, obj):
        cita = obj.cita
        if cita is None:
            return None

        servicio = getattr(cita, "servicio", None)
        return {
            "id_cita": cita.id_cita,
            "fecha_programada": cita.fecha_programada,
            "hora_inicio": cita.hora_inicio,
            "hora_fin": cita.hora_fin,
            "estado": cita.estado,
            "servicio": {
                "id_servicio": getattr(servicio, "id_servicio", None),
                "nombre": getattr(servicio, "nombre", None),
            },
        }

    def get_pedido(self, obj):
        pedido = obj.pedido
        if pedido is None:
            return None

        return {
            "id_pedido": pedido.id_pedido,
            "fecha_pedido": pedido.fecha_pedido,
            "estado_pedido": pedido.estado_pedido,
            "tipo_entrega": pedido.tipo_entrega,
            "total": pedido.total,
        }


class SeguimientoDetailSerializer(SeguimientoListSerializer):
    pass
