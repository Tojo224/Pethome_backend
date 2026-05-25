from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from apps.NotificacionesySeguimiento.permissions import (
    get_user_role_name,
    is_client_role,
    is_veterinarian_role,
)

from ..models import (
    UnidadMovil,
    UnidadMovilAsignacion,
    UnidadMovilAsignacionPersonal,
)


class UnidadMovilAsignacionPersonalReadSerializer(serializers.ModelSerializer):
    id_usuario = serializers.IntegerField(source="usuario_id", read_only=True)
    correo = serializers.CharField(source="usuario.correo", read_only=True)
    role = serializers.CharField(source="usuario.role.nombre", read_only=True)

    class Meta:
        model = UnidadMovilAsignacionPersonal
        fields = [
            "id_asignacion_personal",
            "id_usuario",
            "correo",
            "role",
            "rol_operativo",
            "es_responsable",
            "estado",
        ]


class UnidadMovilAsignacionPersonalWriteSerializer(serializers.Serializer):
    id_usuario = serializers.IntegerField()
    rol_operativo = serializers.ChoiceField(
        choices=UnidadMovilAsignacionPersonal.RolOperativoChoices.choices,
        default=UnidadMovilAsignacionPersonal.RolOperativoChoices.VETERINARIO,
    )
    es_responsable = serializers.BooleanField(default=False)
    estado = serializers.BooleanField(default=True)


class UnidadMovilAsignacionReadSerializer(serializers.ModelSerializer):
    id_unidad = serializers.IntegerField(source="unidad_id", read_only=True)
    unidad = serializers.SerializerMethodField()
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)
    personal = serializers.SerializerMethodField()

    class Meta:
        model = UnidadMovilAsignacion
        fields = [
            "id_asignacion",
            "id_unidad",
            "unidad",
            "id_veterinaria",
            "zona_nombre",
            "zona_descripcion",
            "zona_geojson",
            "fecha_inicio",
            "fecha_fin",
            "hora_inicio",
            "hora_fin",
            "estado",
            "personal",
            "created_at",
            "updated_at",
        ]

    def get_unidad(self, obj):
        return {
            "id_unidad": obj.unidad_id,
            "nombre": obj.unidad.nombre,
            "placa": obj.unidad.placa,
        }

    def get_personal(self, obj):
        queryset = obj.personal_asignado.select_related("usuario", "usuario__role").all()
        return UnidadMovilAsignacionPersonalReadSerializer(queryset, many=True).data


class UnidadMovilAsignacionWriteSerializer(serializers.ModelSerializer):
    id_unidad = serializers.PrimaryKeyRelatedField(
        source="unidad",
        queryset=UnidadMovil.objects.all(),
        write_only=True,
    )
    personal = UnidadMovilAsignacionPersonalWriteSerializer(many=True, write_only=True)

    class Meta:
        model = UnidadMovilAsignacion
        fields = [
            "id_asignacion",
            "id_unidad",
            "zona_nombre",
            "zona_descripcion",
            "zona_geojson",
            "fecha_inicio",
            "fecha_fin",
            "hora_inicio",
            "hora_fin",
            "estado",
            "personal",
        ]
        read_only_fields = ["id_asignacion"]

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
        if unidad and unidad.veterinaria_id != tenant_id:
            raise serializers.ValidationError(
                {"id_unidad": "La unidad movil no pertenece a la veterinaria activa."}
            )

        fecha_inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        fecha_fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))
        hora_inicio = attrs.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        hora_fin = attrs.get("hora_fin", getattr(self.instance, "hora_fin", None))
        estado = attrs.get("estado", getattr(self.instance, "estado", True))
        personal_data = attrs.get("personal")

        if fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha fin no puede ser menor a la fecha inicio."}
            )

        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise serializers.ValidationError(
                {"hora_fin": "La hora fin debe ser mayor a la hora inicio."}
            )

        if personal_data is None and self.instance is not None:
            personal_data = [
                {
                    "id_usuario": row.usuario_id,
                    "rol_operativo": row.rol_operativo,
                    "es_responsable": row.es_responsable,
                    "estado": row.estado,
                }
                for row in self.instance.personal_asignado.all()
            ]

        if not personal_data:
            raise serializers.ValidationError(
                {"personal": "Debes asignar al menos un miembro del personal."}
            )

        responsible_count = sum(1 for item in personal_data if item.get("es_responsable"))
        if responsible_count > 1:
            raise serializers.ValidationError(
                {"personal": "Solo puede existir un responsable principal por asignacion."}
            )

        user_ids = [item["id_usuario"] for item in personal_data]
        if len(user_ids) != len(set(user_ids)):
            raise serializers.ValidationError(
                {"personal": "No puedes repetir el mismo usuario dentro de la asignacion."}
            )

        from apps.AutenticacionySeguridad.models import User

        users = {
            user.id_usuario: user
            for user in User.objects.select_related("role").filter(id_usuario__in=user_ids)
        }
        missing = [user_id for user_id in user_ids if user_id not in users]
        if missing:
            raise serializers.ValidationError(
                {"personal": f"Usuarios no encontrados: {', '.join(map(str, missing))}."}
            )

        veterinarian_count = 0
        for item in personal_data:
            user = users[item["id_usuario"]]
            if user.veterinaria_id != tenant_id:
                raise serializers.ValidationError(
                    {"personal": f"El usuario {user.correo} no pertenece a la veterinaria activa."}
                )

            role_name = get_user_role_name(user)
            if is_client_role(role_name):
                raise serializers.ValidationError(
                    {"personal": f"El usuario {user.correo} no puede ser parte de una unidad movil."}
                )
            if is_veterinarian_role(role_name):
                veterinarian_count += 1

        if veterinarian_count == 0:
            raise serializers.ValidationError(
                {"personal": "La asignacion debe incluir al menos un veterinario."}
            )

        if estado:
            self._validate_unit_overlap(
                unidad=unidad,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
            )
            self._validate_personnel_overlap(
                users=users,
                user_ids=user_ids,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
            )

        attrs["_tenant_id"] = tenant_id
        attrs["_personal_data"] = personal_data
        return attrs

    def _base_overlap_queryset(self):
        queryset = UnidadMovilAsignacion.objects.filter(estado=True)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        return queryset

    def _validate_unit_overlap(self, *, unidad, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
        queryset = self._base_overlap_queryset().filter(unidad=unidad)
        for item in queryset:
            if self._assignment_overlap(item, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
                raise serializers.ValidationError(
                    {"id_unidad": "La unidad ya tiene una asignacion activa en ese rango."}
                )

    def _validate_personnel_overlap(self, *, users, user_ids, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
        queryset = (
            self._base_overlap_queryset()
            .filter(personal_asignado__usuario_id__in=user_ids, personal_asignado__estado=True)
            .distinct()
            .prefetch_related("personal_asignado")
        )
        for item in queryset:
            if not self._assignment_overlap(item, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
                continue

            overlapping_user_ids = set(
                item.personal_asignado.filter(usuario_id__in=user_ids, estado=True).values_list(
                    "usuario_id", flat=True
                )
            )
            if overlapping_user_ids:
                conflicting_emails = ", ".join(users[user_id].correo for user_id in overlapping_user_ids)
                raise serializers.ValidationError(
                    {
                        "personal": (
                            "Existe conflicto de horario para el personal asignado: "
                            f"{conflicting_emails}."
                        )
                    }
                )

    def _assignment_overlap(self, instance, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
        current_end_date = fecha_fin or fecha_inicio
        instance_end_date = instance.fecha_fin or instance.fecha_inicio

        dates_overlap = not (
            instance_end_date < fecha_inicio or current_end_date < instance.fecha_inicio
        )
        if not dates_overlap:
            return False

        if not hora_inicio or not hora_fin or not instance.hora_inicio or not instance.hora_fin:
            return True

        return not (instance.hora_fin <= hora_inicio or hora_fin <= instance.hora_inicio)

    @transaction.atomic
    def create(self, validated_data):
        tenant_id = validated_data.pop("_tenant_id")
        personal_data = validated_data.pop("_personal_data")
        validated_data.pop("personal", None)
        validated_data["veterinaria_id"] = tenant_id
        asignacion = super().create(validated_data)
        self._sync_personal(asignacion, personal_data)
        return asignacion

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("_tenant_id", None)
        personal_data = validated_data.pop("_personal_data", None)
        validated_data.pop("personal", None)
        instance = super().update(instance, validated_data)
        if personal_data is not None:
            instance.personal_asignado.all().delete()
            self._sync_personal(instance, personal_data)
        return instance

    def _sync_personal(self, asignacion, personal_data):
        UnidadMovilAsignacionPersonal.objects.bulk_create(
            [
                UnidadMovilAsignacionPersonal(
                    asignacion=asignacion,
                    usuario_id=item["id_usuario"],
                    rol_operativo=item["rol_operativo"],
                    es_responsable=item.get("es_responsable", False),
                    estado=item.get("estado", True),
                )
                for item in personal_data
            ]
        )
