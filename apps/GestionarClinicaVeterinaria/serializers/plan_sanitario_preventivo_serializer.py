from django.utils import timezone
from rest_framework import serializers

from apps.GestionarClinicaVeterinaria.models import PlanSanitarioPreventivo


class PlanSanitarioPreventivoSerializer(serializers.ModelSerializer):
    mascota_nombre = serializers.CharField(source="mascota.nombre", read_only=True)
    usuario_registro_nombre = serializers.SerializerMethodField()
    tipo_evento_display = serializers.CharField(
        source="get_tipo_evento_display",
        read_only=True,
    )
    estado_plan_display = serializers.CharField(
        source="get_estado_plan_display",
        read_only=True,
    )
    esta_vencido = serializers.SerializerMethodField()
    estado_visual = serializers.SerializerMethodField()
    estado_visual_display = serializers.SerializerMethodField()

    class Meta:
        model = PlanSanitarioPreventivo
        fields = [
            "id_plan_sanitario",
            "mascota",
            "mascota_nombre",
            "veterinaria",
            "usuario_registro",
            "usuario_registro_nombre",
            "tipo_evento",
            "tipo_evento_display",
            "descripcion",
            "fecha_programada",
            "estado_plan",
            "estado_plan_display",
            "esta_vencido",
            "estado_visual",
            "estado_visual_display",
            "observaciones",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id_plan_sanitario",
            "mascota",
            "mascota_nombre",
            "veterinaria",
            "usuario_registro",
            "usuario_registro_nombre",
            "tipo_evento_display",
            "estado_plan_display",
            "esta_vencido",
            "estado_visual",
            "estado_visual_display",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_usuario_registro_nombre(self, obj):
        perfil = getattr(obj.usuario_registro, "perfil", None)
        if perfil and getattr(perfil, "nombre", None):
            return perfil.nombre
        return getattr(obj.usuario_registro, "correo", "")

    def get_esta_vencido(self, obj):
        hoy = timezone.localdate()
        return (
            obj.estado_plan == PlanSanitarioPreventivo.EstadoPlanChoices.PENDIENTE
            and obj.fecha_programada < hoy
        )

    def get_estado_visual(self, obj):
        if self.get_esta_vencido(obj):
            return PlanSanitarioPreventivo.EstadoPlanChoices.VENCIDO
        return obj.estado_plan

    def get_estado_visual_display(self, obj):
        estado_visual = self.get_estado_visual(obj)
        return PlanSanitarioPreventivo.EstadoPlanChoices(estado_visual).label

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        fecha_programada = attrs.get(
            "fecha_programada",
            getattr(instance, "fecha_programada", None),
        )
        estado_plan = attrs.get(
            "estado_plan",
            getattr(instance, "estado_plan", None),
        )

        if not fecha_programada or not estado_plan:
            return attrs

        hoy = timezone.localdate()

        if (
            estado_plan == PlanSanitarioPreventivo.EstadoPlanChoices.PENDIENTE
            and fecha_programada < hoy
        ):
            raise serializers.ValidationError(
                {
                    "estado_plan": "No se puede programar un evento pendiente en una fecha pasada."
                }
            )

        if (
            estado_plan == PlanSanitarioPreventivo.EstadoPlanChoices.VENCIDO
            and fecha_programada >= hoy
        ):
            raise serializers.ValidationError(
                {
                    "estado_plan": "No se puede marcar como vencido un evento cuya fecha aún no ha pasado."
                }
            )

        return attrs
