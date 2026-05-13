from django.utils import timezone
from rest_framework import serializers

from ..models import Suscripcion, Veterinaria
from ..services.auth_security_service import (
    ensure_user_not_blocked,
    get_user_for_login,
    validate_login_password,
)


def get_active_suscripcion(veterinaria_id: int):
    return (
        Suscripcion.objects.filter(veterinaria_id=veterinaria_id)
        .select_related("plan")
        .order_by("-fecha_fin", "-fecha_creacion")
        .first()
    )


class LoginSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    plataforma = serializers.CharField(required=False, default="WEB")

    def validate(self, attrs):
        correo = attrs.get("correo")
        password = attrs.get("password")
        plataforma = str(attrs.get("plataforma", "WEB")).upper()
        attrs["plataforma"] = plataforma

        if plataforma not in {"WEB", "MOVIL"}:
            raise serializers.ValidationError(
                {"detail": "Plataforma invalida. Use WEB o MOVIL.", "code": "PLATAFORMA_INVALIDA"}
            )

        user = get_user_for_login(correo)
        if user:
            ensure_user_not_blocked(user)
        user = validate_login_password(user, password)

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Esta cuenta esta desactivada.", "code": "LOGIN_USUARIO_INACTIVO"}
            )

        if not user.is_superuser:
            veterinaria_id = getattr(user, "veterinaria_id", None)
            if not veterinaria_id:
                raise serializers.ValidationError(
                    {"detail": "El usuario no tiene veterinaria asignada.", "code": "LOGIN_VETERINARIA_INACTIVA"}
                )

            veterinaria = getattr(user, "veterinaria", None)
            if not veterinaria or not getattr(veterinaria, "estado", False):
                raise serializers.ValidationError(
                    {"detail": "La veterinaria no esta activa.", "code": "LOGIN_VETERINARIA_INACTIVA"}
                )

            suscripcion = get_active_suscripcion(veterinaria_id=veterinaria_id)
            if not suscripcion:
                raise serializers.ValidationError(
                    {"detail": "La veterinaria no tiene suscripcion activa.", "code": "LOGIN_SUSCRIPCION_VENCIDA"}
                )

            if suscripcion.estado_suscripcion in {"VENCIDA", "SUSPENDIDA", "CANCELADA"}:
                raise serializers.ValidationError(
                    {"detail": "La suscripcion no esta activa.", "code": "LOGIN_SUSCRIPCION_VENCIDA"}
                )

            if suscripcion.fecha_fin and suscripcion.fecha_fin < timezone.localdate():
                raise serializers.ValidationError(
                    {"detail": "La suscripcion esta vencida.", "code": "LOGIN_SUSCRIPCION_VENCIDA"}
                )

            if plataforma == "MOVIL" and not suscripcion.plan.permite_app_movil:
                raise serializers.ValidationError(
                    {
                        "detail": "Su plan actual no permite el uso de la aplicacion movil.",
                        "code": "LOGIN_APP_MOVIL_NO_PERMITIDA",
                    }
                )

        attrs["user"] = user
        return attrs


class MobileLoginSerializer(serializers.Serializer):
    slug_veterinaria = serializers.SlugField()
    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    plataforma = serializers.CharField(required=False, default="MOVIL")

    def validate(self, attrs):
        attrs["plataforma"] = "MOVIL"
        slug = attrs["slug_veterinaria"]
        correo = attrs["correo"]
        password = attrs["password"]

        veterinaria = Veterinaria.objects.filter(slug=slug, estado=True).first()
        if not veterinaria:
            raise serializers.ValidationError(
                {"detail": "Veterinaria no encontrada o inactiva.", "code": "LOGIN_VETERINARIA_INACTIVA"}
            )

        suscripcion = get_active_suscripcion(veterinaria.id_veterinaria)
        if not suscripcion or suscripcion.estado_suscripcion in {"VENCIDA", "SUSPENDIDA", "CANCELADA"}:
            raise serializers.ValidationError(
                {"detail": "La veterinaria no tiene suscripcion activa.", "code": "LOGIN_SUSCRIPCION_VENCIDA"}
            )

        if suscripcion.fecha_fin and suscripcion.fecha_fin < timezone.localdate():
            raise serializers.ValidationError(
                {"detail": "La suscripcion esta vencida.", "code": "LOGIN_SUSCRIPCION_VENCIDA"}
            )

        if not suscripcion.plan.permite_app_movil:
            raise serializers.ValidationError(
                {"detail": "El plan no permite acceso movil.", "code": "LOGIN_APP_MOVIL_NO_PERMITIDA"}
            )

        user = get_user_for_login(correo)
        if user:
            ensure_user_not_blocked(user)
        user = validate_login_password(user, password)

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Esta cuenta esta desactivada.", "code": "LOGIN_USUARIO_INACTIVO"}
            )

        if user.is_superuser:
            raise serializers.ValidationError(
                {"detail": "SuperAdmin no puede usar login movil de cliente.", "code": "LOGIN_MOVIL_NO_PERMITIDO"}
            )

        if user.veterinaria_id != veterinaria.id_veterinaria:
            raise serializers.ValidationError(
                {"detail": "El usuario no pertenece a la veterinaria seleccionada.", "code": "LOGIN_OTRO_TENANT"}
            )

        role_name = (user.role.nombre if user.role_id else "").upper()
        allowed_roles = {"CLIENT", "ADMIN", "VETERINARIO", "DUEÑO", "OWNER"}
        if role_name not in allowed_roles:
            raise serializers.ValidationError(
                {"detail": f"El rol {role_name} no tiene permitido el acceso movil.", "code": "LOGIN_MOVIL_NO_PERMITIDO"}
            )

        attrs["user"] = user
        attrs["veterinaria"] = veterinaria
        return attrs


class MobileRegisterSerializer(serializers.Serializer):
    slug_veterinaria = serializers.SlugField()
    nombre = serializers.CharField(max_length=150)
    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)
