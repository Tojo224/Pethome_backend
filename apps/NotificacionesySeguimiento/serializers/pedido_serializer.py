from rest_framework import serializers

from ..models import Pedido
from ..permissions import is_client
from .detallepedido_serializer import DetallePedidoSerializer


class PedidoSeguimientoRelacionadoSerializer(serializers.Serializer):
    id_seguimiento = serializers.IntegerField(read_only=True)
    tipo_seguimiento = serializers.CharField(read_only=True)
    estado_anterior = serializers.CharField(read_only=True, allow_null=True)
    estado_actual = serializers.CharField(read_only=True)
    descripcion = serializers.CharField(read_only=True, allow_null=True)
    fecha_hora = serializers.DateTimeField(read_only=True)
    visible_cliente = serializers.BooleanField(read_only=True)


class PedidoListSerializer(serializers.ModelSerializer):
    usuario_id = serializers.IntegerField(source="usuario.id_usuario", read_only=True)
    usuario_correo = serializers.EmailField(source="usuario.correo", read_only=True)
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = [
            "id_pedido",
            "usuario_id",
            "usuario_correo",
            "usuario_nombre",
            "fecha_pedido",
            "tipo_entrega",
            "estado_pedido",
            "subtotal",
            "costo_envio",
            "total",
            "observacion",
            "motivo_cancelacion",
            "estado",
        ]

    def get_usuario_nombre(self, obj):
        perfil = getattr(obj.usuario, "perfil", None)
        return getattr(perfil, "nombre", None)


class PedidoDetailSerializer(PedidoListSerializer):
    direccion_entrega = serializers.CharField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    fecha_actualizacion = serializers.DateTimeField(read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    seguimientos = serializers.SerializerMethodField()

    class Meta(PedidoListSerializer.Meta):
        fields = PedidoListSerializer.Meta.fields + [
            "direccion_entrega",
            "fecha_creacion",
            "fecha_actualizacion",
            "detalles",
            "seguimientos",
        ]

    def get_seguimientos(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        is_client_user = bool(user and is_client(user))

        data = []
        queryset = obj.seguimientos.all().order_by("-fecha_hora")
        if is_client_user:
            queryset = queryset.filter(visible_cliente=True)

        for seguimiento in queryset:
            data.append(
                {
                    "id_seguimiento": seguimiento.id_seguimiento,
                    "tipo_seguimiento": seguimiento.tipo_seguimiento,
                    "estado_anterior": seguimiento.estado_anterior,
                    "estado_actual": seguimiento.estado_actual,
                    "descripcion": seguimiento.descripcion,
                    "fecha_hora": seguimiento.fecha_hora,
                    "visible_cliente": seguimiento.visible_cliente,
                }
            )
        serializer = PedidoSeguimientoRelacionadoSerializer(data, many=True)
        return serializer.data
