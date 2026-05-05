from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers

from ..models.suscripcion import Suscripcion


class LoginSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    plataforma = serializers.ChoiceField(
        choices=["web", "movil"], default="web", required=False
    )

    def validate(self, attrs):
        correo = attrs.get("correo")
        password = attrs.get("password")
        plataforma = attrs.get("plataforma")

        user = authenticate(
            request=self.context.get("request"),
            username=correo,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                {"detail": "Correo o contraseña incorrectos.", "code": "LOGIN_FALLIDO"}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Esta cuenta está desactivada.", "code": "LOGIN_USUARIO_INACTIVO"}
            )

        if not user.is_superuser:
            veterinaria_id = getattr(user, "veterinaria_id", None)
            if not veterinaria_id:
                raise serializers.ValidationError(
                    {"detail": "El usuario no tiene veterinaria asignada.", "code": "LOGIN_VETERINARIA_INACTIVA"}
                )

            suscripcion = (
                Suscripcion.objects.filter(veterinaria_id=veterinaria_id)
                .order_by("-fecha_fin", "-fecha_creacion")
                .first()
            )

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

            # Validar permiso de app móvil
            if plataforma == "movil" and not suscripcion.plan.permite_app_movil:
                raise serializers.ValidationError(
                    {
                        "detail": "Su plan actual no permite el uso de la aplicación móvil.",
                        "code": "LOGIN_APP_MOVIL_NO_PERMITIDA"
                    }
                )

        attrs["user"] = user
        return attrs
