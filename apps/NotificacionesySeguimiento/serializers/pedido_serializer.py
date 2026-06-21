from rest_framework import serializers
from django.db.models import Q

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

    @staticmethod
    def _payment_priority(estado_pago):
        priorities = {
            Pago.EstadoPago.PAGADO: 6,
            Pago.EstadoPago.EN_PROCESO: 5,
            Pago.EstadoPago.PENDIENTE: 4,
            Pago.EstadoPago.ANULADO: 3,
            Pago.EstadoPago.RECHAZADO: 2,
            Pago.EstadoPago.FALLIDO: 1,
        }
        return priorities.get(estado_pago, 0)

    @classmethod
    def _select_best_payment(cls, pagos_queryset):
        pagos = list(pagos_queryset)
        if not pagos:
            return None

        pagos.sort(
            key=lambda pago: (
                cls._payment_priority(getattr(pago, "estado_pago", None)),
                getattr(pago, "fecha_confirmacion", None) or getattr(pago, "fecha_creacion", None),
            ),
            reverse=True,
        )
        return pagos[0]

    def get_estado_pago(self, obj):
        pagos = getattr(obj, "_prefetched_payments", None)
        if pagos is None:
            filtros = Q(
                tipo_referencia=Pago.TipoReferencia.PEDIDO_MOVIL,
                referencia_id=obj.id_pedido,
            )

            if getattr(obj, "cita_id", None):
                filtros |= Q(
                    tipo_referencia=Pago.TipoReferencia.CITA_SERVICIO,
                    referencia_id=obj.cita_id,
                )

            pago = self._select_best_payment(Pago.objects.filter(filtros).order_by("-fecha_creacion"))
            return getattr(pago, "estado_pago", None)

        pago = self._select_best_payment(pagos)
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
