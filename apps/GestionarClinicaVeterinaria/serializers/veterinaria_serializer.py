from django.utils.text import slugify
from rest_framework import serializers

from apps.AutenticacionySeguridad.models.veterinaria import Veterinaria
from apps.AutenticacionySeguridad.models.suscripcion import Suscripcion


class VeterinariaSerializer(serializers.ModelSerializer):
    plan_id = serializers.SerializerMethodField()
    plan_nombre = serializers.SerializerMethodField()
    suscripcion_estado = serializers.SerializerMethodField()
    suscripcion_fecha_inicio = serializers.SerializerMethodField()
    suscripcion_fecha_fin = serializers.SerializerMethodField()
    permite_app_movil = serializers.SerializerMethodField()
    permite_reportes = serializers.SerializerMethodField()
    permite_backup = serializers.SerializerMethodField()
    limite_usuarios = serializers.SerializerMethodField()
    limite_mascotas = serializers.SerializerMethodField()

    class Meta:
        model = Veterinaria
        fields = [
            "id_veterinaria",
            "nombre",
            "slug",
            "nit",
            "correo",
            "telefono",
            "direccion",
            "logo",
            "estado",
            "permite_auto_registro_clientes",
            "fecha_creacion",
            "plan_id",
            "plan_nombre",
            "suscripcion_estado",
            "suscripcion_fecha_inicio",
            "suscripcion_fecha_fin",
            "permite_app_movil",
            "permite_reportes",
            "permite_backup",
            "limite_usuarios",
            "limite_mascotas",
        ]
        read_only_fields = ["id_veterinaria", "fecha_creacion"]

    def validate_slug(self, value):
        value = (value or "").strip().lower()
        if not value:
            raise serializers.ValidationError("El slug es requerido.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        nombre = (attrs.get("nombre") or "").strip()
        slug = (attrs.get("slug") or "").strip().lower()

        if not slug and nombre:
            attrs["slug"] = slugify(nombre)

        return attrs

    def _active_subscription(self, obj):
        cached = getattr(obj, "_cached_active_subscription", None)
        if cached is not None:
            return cached

        sub = (
            Suscripcion.objects.filter(veterinaria_id=obj.id_veterinaria)
            .select_related("plan")
            .order_by("-fecha_fin", "-fecha_creacion")
            .first()
        )
        setattr(obj, "_cached_active_subscription", sub)
        return sub

    def get_plan_id(self, obj):
        sub = self._active_subscription(obj)
        return sub.plan_id if sub else None

    def get_plan_nombre(self, obj):
        sub = self._active_subscription(obj)
        return sub.plan.nombre if sub and sub.plan else None

    def get_suscripcion_estado(self, obj):
        sub = self._active_subscription(obj)
        return sub.estado_suscripcion if sub else None

    def get_suscripcion_fecha_inicio(self, obj):
        sub = self._active_subscription(obj)
        return sub.fecha_inicio if sub else None

    def get_suscripcion_fecha_fin(self, obj):
        sub = self._active_subscription(obj)
        return sub.fecha_fin if sub else None

    def get_permite_app_movil(self, obj):
        sub = self._active_subscription(obj)
        return bool(sub.plan.permite_app_movil) if sub and sub.plan else False

    def get_permite_reportes(self, obj):
        sub = self._active_subscription(obj)
        return bool(sub.plan.permite_reportes) if sub and sub.plan else False

    def get_permite_backup(self, obj):
        sub = self._active_subscription(obj)
        return bool(sub.plan.permite_backup) if sub and sub.plan else False

    def get_limite_usuarios(self, obj):
        sub = self._active_subscription(obj)
        return int(sub.plan.limite_usuarios) if sub and sub.plan else 0

    def get_limite_mascotas(self, obj):
        sub = self._active_subscription(obj)
        return int(sub.plan.limite_mascotas) if sub and sub.plan else 0
