from datetime import datetime
import unicodedata

from rest_framework import serializers
from django.utils import timezone

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models import User
from apps.GestionServiciosyReserva.models import Cita, DetalleRuta, RutaProgramada, UnidadMovil
from apps.NotificacionesySeguimiento.models import Pedido, Seguimiento


TRACKED_ROUTE_STATES = {
    DetalleRuta.EstadoChoices.EN_CAMINO,
    DetalleRuta.EstadoChoices.ATENDIENDO,
    DetalleRuta.EstadoChoices.COMPLETADA,
    DetalleRuta.EstadoChoices.CANCELADA,
    DetalleRuta.EstadoChoices.INCIDENCIA,
}

TRACKED_ROUTE_DESCRIPTIONS = {
    DetalleRuta.EstadoChoices.EN_CAMINO: "Veterinario en camino al domicilio",
    DetalleRuta.EstadoChoices.ATENDIENDO: "Inicio de atencion en domicilio",
    DetalleRuta.EstadoChoices.COMPLETADA: "Servicio a domicilio finalizado",
    DetalleRuta.EstadoChoices.CANCELADA: "Servicio a domicilio cancelado",
    DetalleRuta.EstadoChoices.INCIDENCIA: "Se registro una incidencia en la ruta",
}

ACTIVE_ROUTE_STATES = {
    RutaProgramada.EstadoChoices.PROGRAMADA,
    RutaProgramada.EstadoChoices.EN_PROCESO,
}


def normalize_role_name(value):
    raw = unicodedata.normalize("NFD", value or "")
    return "".join(char for char in raw if unicodedata.category(char) != "Mn").strip().upper()


class UnidadMovilSerializer(serializers.ModelSerializer):
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)

    class Meta:
        model = UnidadMovil
        fields = [
            "id_unidad",
            "nombre",
            "placa",
            "descripcion",
            "estado",
            "id_veterinaria",
        ]
        read_only_fields = ["id_unidad", "estado", "id_veterinaria"]


class UnidadMovilWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMovil
        fields = ["id_unidad", "nombre", "placa", "descripcion", "estado"]
        read_only_fields = ["id_unidad"]


class UnidadMovilCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMovil
        fields = ["id_unidad", "nombre", "placa"]


class VeterinarioCompactSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id_usuario", "correo"]


class ClienteCompactSerializer(serializers.Serializer):
    id_usuario = serializers.IntegerField()
    nombre = serializers.CharField(allow_null=True)
    telefono = serializers.CharField(allow_null=True)


class ServicioCompactSerializer(serializers.Serializer):
    id_servicio = serializers.IntegerField()
    nombre = serializers.CharField(allow_null=True)


class MascotaCompactSerializer(serializers.Serializer):
    id_mascota = serializers.IntegerField()
    nombre = serializers.CharField(allow_null=True)


class SeguimientoRutaSerializer(serializers.Serializer):
    estado_actual = serializers.CharField(read_only=True)
    descripcion = serializers.CharField(read_only=True, allow_null=True)
    fecha_hora = serializers.DateTimeField(read_only=True)
    origen = serializers.CharField(read_only=True, required=False)


class CitaRutaSerializer(serializers.ModelSerializer):
    servicio = serializers.SerializerMethodField()
    mascota = serializers.SerializerMethodField()
    cliente = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = [
            "id_cita",
            "fecha_programada",
            "hora_inicio",
            "hora_fin",
            "modalidad",
            "direccion_cita",
            "estado",
            "servicio",
            "mascota",
            "cliente",
        ]

    def get_servicio(self, obj):
        servicio = getattr(obj, "servicio", None)
        return {
            "id_servicio": getattr(servicio, "id_servicio", None),
            "nombre": getattr(servicio, "nombre", None),
        }

    def get_mascota(self, obj):
        mascota = getattr(obj, "mascota", None)
        return {
            "id_mascota": getattr(mascota, "id_mascota", None),
            "nombre": getattr(mascota, "nombre", None),
        }

    def get_cliente(self, obj):
        usuario = getattr(obj, "usuario", None)
        perfil = getattr(usuario, "perfil", None)
        return {
            "id_usuario": getattr(usuario, "id_usuario", None),
            "nombre": getattr(perfil, "nombre", None),
            "telefono": getattr(perfil, "telefono", None),
        }


class PedidoRutaSerializer(serializers.ModelSerializer):
    cliente = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = [
            "id_pedido",
            "fecha_pedido",
            "tipo_entrega",
            "estado_pedido",
            "direccion_entrega",
            "total",
            "cliente",
        ]

    def get_cliente(self, obj):
        usuario = getattr(obj, "usuario", None)
        perfil = getattr(usuario, "perfil", None)
        return {
            "id_usuario": getattr(usuario, "id_usuario", None),
            "nombre": getattr(perfil, "nombre", None),
            "telefono": getattr(perfil, "telefono", None),
        }


class DetalleRutaReadSerializer(serializers.ModelSerializer):
    cita = serializers.SerializerMethodField()
    pedido = serializers.SerializerMethodField()
    tipo_referencia = serializers.SerializerMethodField()
    referencia_id = serializers.SerializerMethodField()
    seguimiento = serializers.SerializerMethodField()

    class Meta:
        model = DetalleRuta
        fields = [
            "id_detalle_ruta",
            "orden",
            "hora_estimada",
            "estado",
            "cita",
            "pedido",
            "tipo_referencia",
            "referencia_id",
            "seguimiento",
        ]

    def get_cita(self, obj):
        if obj.cita is None:
            return None
        return CitaRutaSerializer(obj.cita).data

    def get_pedido(self, obj):
        if obj.pedido is None:
            return None
        return PedidoRutaSerializer(obj.pedido).data

    def get_tipo_referencia(self, obj):
        return "PEDIDO" if obj.pedido_id else "CITA"

    def get_referencia_id(self, obj):
        return obj.pedido_id or obj.cita_id

    def get_seguimiento(self, obj):
        if obj.pedido_id:
            queryset = obj.pedido.seguimientos.filter(
                tipo_seguimiento="RUTA",
                estado=True,
            ).order_by("fecha_hora")
            data = [
                {
                    "estado_actual": item.estado_actual,
                    "descripcion": item.descripcion,
                    "fecha_hora": item.fecha_hora,
                    "origen": "PEDIDO",
                }
                for item in queryset
            ]
            return SeguimientoRutaSerializer(data, many=True).data

        if obj.cita_id:
            queryset = obj.cita.seguimientos.filter(
                tipo_seguimiento="RUTA",
                estado=True,
            ).order_by("fecha_hora")
            data = [
                {
                    "estado_actual": item.estado_actual,
                    "descripcion": item.descripcion,
                    "fecha_hora": item.fecha_hora,
                    "origen": "CITA",
                }
                for item in queryset
            ]
            return SeguimientoRutaSerializer(data, many=True).data

        return []


class RutaProgramadaReadSerializer(serializers.ModelSerializer):
    unidad = UnidadMovilCompactSerializer(read_only=True)
    veterinario = VeterinarioCompactSerializer(read_only=True)
    detalle = serializers.SerializerMethodField()
    cantidad_citas = serializers.IntegerField(read_only=True)

    class Meta:
        model = RutaProgramada
        fields = [
            "id_ruta",
            "nombre",
            "fecha",
            "estado",
            "unidad",
            "veterinario",
            "cantidad_citas",
            "detalle",
        ]

    def get_detalle(self, obj):
        detalles = obj.detalles.all().order_by("orden")
        return DetalleRutaReadSerializer(detalles, many=True).data


class RutaProgramadaWriteSerializer(serializers.ModelSerializer):
    id_unidad = serializers.PrimaryKeyRelatedField(
        source="unidad",
        queryset=UnidadMovil.objects.all(),
        write_only=True,
    )
    id_veterinario = serializers.PrimaryKeyRelatedField(
        source="veterinario",
        queryset=User.objects.all(),
        write_only=True,
    )

    class Meta:
        model = RutaProgramada
        fields = [
            "id_ruta",
            "nombre",
            "fecha",
            "estado",
            "id_unidad",
            "id_veterinario",
        ]
        read_only_fields = ["id_ruta"]

    def validate(self, attrs):
        request = self.context["request"]
        tenant_id = getattr(getattr(request, "tenant", None), "id", None) or getattr(
            request.user,
            "veterinaria_id",
            None,
        )

        if tenant_id is None:
            raise serializers.ValidationError("No se pudo resolver la veterinaria activa.")

        unidad = attrs.get("unidad", getattr(self.instance, "unidad", None))
        veterinario = attrs.get("veterinario", getattr(self.instance, "veterinario", None))

        if unidad and unidad.veterinaria_id != tenant_id:
            raise serializers.ValidationError(
                {
                    "id_unidad": (
                        "La unidad movil no pertenece a la veterinaria actual. "
                        f"Sesion={tenant_id}, unidad={unidad.veterinaria_id}."
                    )
                }
            )

        if veterinario and veterinario.veterinaria_id != tenant_id:
            raise serializers.ValidationError(
                {
                    "id_veterinario": (
                        "El veterinario asignado no pertenece a la veterinaria actual. "
                        f"Sesion={tenant_id}, veterinario={veterinario.veterinaria_id}."
                    )
                }
            )

        role_name = normalize_role_name(getattr(getattr(veterinario, "role", None), "nombre", ""))
        if role_name not in {
            normalize_role_name(RoleEnum.VETERINARIAN.value),
            "VETERINARIO",
        }:
            raise serializers.ValidationError(
                {"id_veterinario": "El usuario asignado debe tener rol VETERINARIAN."}
            )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        tenant_id = getattr(getattr(request, "tenant", None), "id", None) or getattr(
            request.user,
            "veterinaria_id",
            None,
        )
        validated_data["veterinaria_id"] = tenant_id
        return super().create(validated_data)


class DetalleRutaCreateSerializer(serializers.ModelSerializer):
    id_cita = serializers.PrimaryKeyRelatedField(
        source="cita",
        queryset=Cita.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    id_pedido = serializers.PrimaryKeyRelatedField(
        source="pedido",
        queryset=Pedido.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = DetalleRuta
        fields = ["id_detalle_ruta", "id_cita", "id_pedido", "orden", "hora_estimada", "estado"]
        read_only_fields = ["id_detalle_ruta"]

    @staticmethod
    def _pedido_operativo_date(pedido):
        cita = getattr(pedido, "cita", None)
        if cita is not None:
            return cita.fecha_programada
        fecha_pedido = getattr(pedido, "fecha_pedido", None)
        if fecha_pedido is None:
            return None
        if timezone.is_aware(fecha_pedido):
            return timezone.localtime(fecha_pedido).date()
        return fecha_pedido.date() if isinstance(fecha_pedido, datetime) else fecha_pedido

    @staticmethod
    def _validate_same_route_reference(ruta, cita=None, pedido=None):
        if cita and DetalleRuta.objects.filter(ruta=ruta, cita=cita).exists():
            raise serializers.ValidationError(
                {"id_cita": "La cita ya esta asignada a esta ruta."}
            )

        if pedido and DetalleRuta.objects.filter(ruta=ruta, pedido=pedido).exists():
            raise serializers.ValidationError(
                {"id_pedido": "El pedido ya esta asignado a esta ruta."}
            )

        if cita and DetalleRuta.objects.filter(ruta=ruta, pedido__cita=cita).exists():
            raise serializers.ValidationError(
                {"id_cita": "La cita ya esta representada en esta ruta por un pedido ligado al servicio."}
            )

        if pedido and pedido.cita_id and DetalleRuta.objects.filter(
            ruta=ruta,
            cita_id=pedido.cita_id,
        ).exclude(pedido=pedido).exists():
            raise serializers.ValidationError(
                {"id_pedido": "La cita relacionada con este pedido ya esta asignada a esta ruta."}
            )

    @staticmethod
    def _validate_active_reference_conflict(ruta, cita=None, pedido=None):
        if cita and DetalleRuta.objects.filter(
            cita=cita,
            ruta__estado__in=ACTIVE_ROUTE_STATES,
        ).exclude(ruta=ruta).exists():
            raise serializers.ValidationError(
                {"id_cita": "La cita ya esta asignada a otra ruta activa."}
            )

        if cita and DetalleRuta.objects.filter(
            pedido__cita=cita,
            ruta__estado__in=ACTIVE_ROUTE_STATES,
        ).exclude(ruta=ruta).exists():
            raise serializers.ValidationError(
                {"id_cita": "La cita ya esta cubierta por un pedido asignado a otra ruta activa."}
            )

        if pedido and DetalleRuta.objects.filter(
            pedido=pedido,
            ruta__estado__in=ACTIVE_ROUTE_STATES,
        ).exclude(ruta=ruta).exists():
            raise serializers.ValidationError(
                {"id_pedido": "El pedido ya esta asignado a otra ruta activa."}
            )

        if pedido and pedido.cita_id and DetalleRuta.objects.filter(
            cita_id=pedido.cita_id,
            ruta__estado__in=ACTIVE_ROUTE_STATES,
        ).exclude(ruta=ruta).exists():
            raise serializers.ValidationError(
                {"id_pedido": "La cita relacionada con este pedido ya esta asignada a otra ruta activa."}
            )

    def validate(self, attrs):
        ruta = self.context["ruta"]
        cita = attrs.get("cita")
        pedido = attrs.get("pedido")

        if not cita and not pedido:
            raise serializers.ValidationError(
                "Debes seleccionar una cita o un pedido para agregarlo a la ruta."
            )

        if cita and pedido:
            if pedido.cita_id is None or pedido.cita_id != cita.id_cita:
                raise serializers.ValidationError(
                    {
                        "id_pedido": (
                            "Si envias cita y pedido al mismo tiempo, el pedido debe estar ligado a esa misma cita."
                        )
                    }
                )

        if cita:
            if cita.modalidad != Cita.ModalidadChoices.DOMICILIO:
                raise serializers.ValidationError(
                    {"id_cita": "Solo se pueden agregar citas con modalidad DOMICILIO."}
                )

            if cita.veterinaria_id != ruta.veterinaria_id:
                raise serializers.ValidationError(
                    {"id_cita": "La cita no pertenece a la misma veterinaria que la ruta."}
                )

            if cita.fecha_programada != ruta.fecha:
                raise serializers.ValidationError(
                    {"id_cita": "La fecha de la cita debe coincidir con la fecha de la ruta."}
                )

        if pedido:
            if pedido.veterinaria_id != ruta.veterinaria_id:
                raise serializers.ValidationError(
                    {"id_pedido": "El pedido no pertenece a la misma veterinaria que la ruta."}
                )

            if pedido.tipo_entrega != Pedido.TIPOS_ENTREGA[0][0]:
                raise serializers.ValidationError(
                    {"id_pedido": "Solo se pueden asignar a unidad movil pedidos con entrega DOMICILIO."}
                )

            if pedido.estado_pedido in {"CANCELADO", "ENTREGADO"}:
                raise serializers.ValidationError(
                    {"id_pedido": "El pedido ya no esta disponible para ser asignado a una ruta activa."}
                )

            fecha_operativa = self._pedido_operativo_date(pedido)
            if fecha_operativa != ruta.fecha:
                raise serializers.ValidationError(
                    {
                        "id_pedido": (
                            "La fecha operativa del pedido debe coincidir con la fecha de la ruta."
                        )
                    }
                )

            if pedido.cita_id and cita is None:
                attrs["cita"] = pedido.cita
                cita = pedido.cita

        self._validate_same_route_reference(ruta, cita=cita, pedido=pedido)
        self._validate_active_reference_conflict(ruta, cita=cita, pedido=pedido)

        orden = attrs["orden"]
        if DetalleRuta.objects.filter(ruta=ruta, orden=orden).exists():
            raise serializers.ValidationError(
                {"orden": "El orden ya esta en uso dentro de esta ruta."}
            )

        return attrs

    def create(self, validated_data):
        validated_data["ruta"] = self.context["ruta"]
        return super().create(validated_data)


class DetalleRutaUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleRuta
        fields = ["orden", "hora_estimada", "estado"]

    def validate(self, attrs):
        orden = attrs.get("orden")
        if orden is not None:
            exists = DetalleRuta.objects.filter(
                ruta=self.instance.ruta,
                orden=orden,
            ).exclude(pk=self.instance.pk)
            if exists.exists():
                raise serializers.ValidationError(
                    {"orden": "El orden ya esta en uso dentro de esta ruta."}
                )

        ruta = self.instance.ruta
        cita = self.instance.cita
        pedido = self.instance.pedido

        if ruta.estado in {RutaProgramada.EstadoChoices.CANCELADA, RutaProgramada.EstadoChoices.FINALIZADA}:
            raise serializers.ValidationError(
                {"detail": "No se puede modificar un detalle de una ruta cerrada."}
            )

        fecha_operativa = cita.fecha_programada if cita is not None else None
        if fecha_operativa is None and pedido is not None:
            fecha_operativa = DetalleRutaCreateSerializer._pedido_operativo_date(pedido)

        if fecha_operativa != ruta.fecha:
            raise serializers.ValidationError(
                {"detail": "La referencia asociada ya no coincide con la fecha operativa de la ruta."}
            )

        return attrs

    def update(self, instance, validated_data):
        previous_state = instance.estado
        instance = super().update(instance, validated_data)

        new_state = instance.estado
        if new_state != previous_state and new_state in TRACKED_ROUTE_STATES:
            request = self.context.get("request")
            seguimiento_kwargs = {
                "tipo_seguimiento": "RUTA",
                "estado_anterior": previous_state,
                "estado_actual": new_state,
                "descripcion": TRACKED_ROUTE_DESCRIPTIONS.get(new_state, ""),
                "visible_cliente": True,
                "usuario": getattr(request, "user", None),
            }
            if instance.pedido_id:
                Seguimiento.objects.create(
                    **seguimiento_kwargs,
                    pedido=instance.pedido,
                    veterinaria_id=instance.pedido.veterinaria_id,
                )
            elif instance.cita_id:
                Seguimiento.objects.create(
                    **seguimiento_kwargs,
                    cita=instance.cita,
                    veterinaria_id=instance.cita.veterinaria_id,
                )

        return instance
