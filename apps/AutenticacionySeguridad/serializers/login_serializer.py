from rest_framework import serializers
from django.contrib.auth import authenticate

from apps.AutenticacionySeguridad.models import User


class LoginSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        correo = attrs.get("correo")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=correo,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                "Correo o contraseña incorrectos.", code="authorization"
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "Esta cuenta está desactivada.", code="authorization"
            )

        attrs["user"] = user
        return attrs
