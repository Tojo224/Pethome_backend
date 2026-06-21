from rest_framework import serializers

from apps.GestiondeVentasyPagos.models import Pago

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


class PedidoServicioRelacionadoSerializer(serializers.Serializer):
    id_servicio = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(read_only=True)


class PedidoCitaRelacionadaSerializer(serializers.Serializer):
    id_cita = serializers.IntegerField(read_only=True)
    fecha_programada = serializers.DateField(read_only=True)
    hora_inicio = serializers.TimeField(read_only=True)
    estado = serializers.CharField(read_only=True)
    servicio = PedidoServicioRelacionadoSerializer(read_only=True)


class PedidoListSerializer(serializers.ModelSerializer):
    usuario_id = serializers.IntegerField(source="usuario.id_usuario", read_only=True)
    usuario_correo = serializers.EmailField(source="usuario.correo", read_only=True)
    usuario_nombre = serializers.SerializerMethodField()
    cita = serializers.SerializerMethodField()
    estado_pago = serializers.SerializerMethodField()

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
            "cita",
            "subtotal",
            "costo_envio",
            "total",
            "observacion",
            "motivo_cancelacion",
            "estado_pago",
            "estado",
        ]

    def get_usuario_nombre(self, obj):
        perfil = getattr(obj.usuario, "perfil", None)
        return getattr(perfil, "nombre", None)

    def get_cita(self, obj):
        cita = getattr(obj, "cita", None)
        if cita is None:
            return None

        servicio = getattr(cita, "servicio", None)
        payload = {
            "id_cita": cita.id_cita,
            "fecha_programada": cita.fecha_programada,
            "hora_inicio": cita.hora_inicio,
            "estado": cita.estado,
            "servicio": None,
        }

        if servicio is not None:
            payload["servicio"] = {
                "id_servicio": servicio.id_servicio,
                "nombre": servicio.nombre,
            }

        return PedidoCitaRelacionadaSerializer(payload).data

    def get_estado_pago(self, obj):
        pagos = getattr(obj, "_prefetched_payments", None)
        if pagos is None:
            pagos = Pago.objects.filter(
                veterinaria_id=obj.veterinaria_id,
                tipo_referencia=Pago.TipoReferencia.PEDIDO_MOVIL,
                referencia_id=obj.id_pedido,
            ).order_by("-fecha_creacion")

        pago = next(iter(pagos), None)
        return getattr(pago, "estado_pago", None)


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
        queryset = obj.seguimientos.order_by("-fecha_hora", "-id_seguimiento")
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
