import unicodedata

from rest_framework import serializers

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models import User
from apps.GestionServiciosyReserva.models import Cita, DetalleRuta, RutaProgramada, UnidadMovil
from apps.NotificacionesySeguimiento.models import Seguimiento


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


class SeguimientoRutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seguimiento
        fields = ["estado_actual", "descripcion", "fecha_hora"]


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


class DetalleRutaReadSerializer(serializers.ModelSerializer):
    cita = CitaRutaSerializer(read_only=True)
    seguimiento = serializers.SerializerMethodField()

    class Meta:
        model = DetalleRuta
        fields = [
            "id_detalle_ruta",
            "orden",
            "hora_estimada",
            "estado",
            "cita",
            "seguimiento",
        ]

    def get_seguimiento(self, obj):
        queryset = obj.cita.seguimientos.filter(
            tipo_seguimiento="RUTA",
            estado=True,
        ).order_by("fecha_hora")
        return SeguimientoRutaSerializer(queryset, many=True).data


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
    )

    class Meta:
        model = DetalleRuta
        fields = ["id_detalle_ruta", "id_cita", "orden", "hora_estimada", "estado"]
        read_only_fields = ["id_detalle_ruta"]

    def validate(self, attrs):
        ruta = self.context["ruta"]
        cita = attrs["cita"]

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

        if DetalleRuta.objects.filter(ruta=ruta, cita=cita).exists():
            raise serializers.ValidationError(
                {"id_cita": "La cita ya esta asignada a esta ruta."}
            )

        if DetalleRuta.objects.filter(
            cita=cita,
            ruta__estado__in=ACTIVE_ROUTE_STATES,
        ).exclude(ruta=ruta).exists():
            raise serializers.ValidationError(
                {
                    "id_cita": (
                        "La cita ya esta asignada a otra ruta activa."
                    )
                }
            )

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

        if ruta.estado in {RutaProgramada.EstadoChoices.CANCELADA, RutaProgramada.EstadoChoices.FINALIZADA}:
            raise serializers.ValidationError(
                {"detail": "No se puede modificar un detalle de una ruta cerrada."}
            )

        if cita.fecha_programada != ruta.fecha:
            raise serializers.ValidationError(
                {"detail": "La cita ya no coincide con la fecha de la ruta."}
            )

        return attrs

    def update(self, instance, validated_data):
        previous_state = instance.estado
        instance = super().update(instance, validated_data)

        new_state = instance.estado
        if new_state != previous_state and new_state in TRACKED_ROUTE_STATES:
            request = self.context.get("request")
            Seguimiento.objects.create(
                tipo_seguimiento="RUTA",
                estado_anterior=previous_state,
                estado_actual=new_state,
                descripcion=TRACKED_ROUTE_DESCRIPTIONS.get(new_state, ""),
                visible_cliente=True,
                cita=instance.cita,
                usuario=getattr(request, "user", None),
                veterinaria_id=instance.cita.veterinaria_id,
            )

        return instance
