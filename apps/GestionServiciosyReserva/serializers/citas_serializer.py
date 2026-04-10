from rest_framework import serializers

from apps.AutenticacionySeguridad.enums.roles import RoleEnum

from ..models import Cita


class CitaSerializer(serializers.ModelSerializer):
    usuario = serializers.IntegerField(source="usuario.id_usuario", read_only=True)
    correo_usuario = serializers.EmailField(source="usuario.correo", read_only=True)
    mascota_nombre = serializers.CharField(source="mascota.nombre", read_only=True)
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True)
    precio = serializers.DecimalField(
        source="precio_servicio.precio",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Cita
        fields = [
            "id_cita",
            "usuario",
            "correo_usuario",
            "mascota",
            "mascota_nombre",
            "servicio",
            "servicio_nombre",
            "precio_servicio",
            "precio",
            "fecha_generada",
            "fecha_confirmacion",
            "fecha_programada",
            "hora_inicio",
            "hora_fin",
            "modalidad",
            "direccion_cita",
            "descripcion",
            "estado",
            "motivo_cancelacion",
        ]
        read_only_fields = [
            "id_cita",
            "usuario",
            "correo_usuario",
            "mascota_nombre",
            "servicio_nombre",
            "precio",
            "fecha_generada",
            "fecha_confirmacion",
            "hora_fin",
            "estado",
            "motivo_cancelacion",
        ]

    def validate(self, data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        mascota = data.get("mascota", getattr(self.instance, "mascota", None))
        servicio = data.get("servicio", getattr(self.instance, "servicio", None))
        precio_servicio = data.get(
            "precio_servicio",
            getattr(self.instance, "precio_servicio", None),
        )
        modalidad = data.get("modalidad", getattr(self.instance, "modalidad", None))
        direccion_cita = data.get(
            "direccion_cita",
            getattr(self.instance, "direccion_cita", None),
        )

        if (
            mascota
            and user
            and getattr(getattr(user, "role", None), "nombre", None) == RoleEnum.CLIENT.value
            and mascota.usuario_id != user.id_usuario
        ):
            raise serializers.ValidationError(
                {"mascota": "Solo puedes solicitar citas para tus propias mascotas."}
            )

        if servicio and not servicio.estado:
            raise serializers.ValidationError(
                {"servicio": "No se puede solicitar una cita para un servicio inactivo."}
            )

        if precio_servicio and not precio_servicio.estado:
            raise serializers.ValidationError(
                {"precio_servicio": "El precio seleccionado no está disponible."}
            )

        if servicio and precio_servicio and precio_servicio.servicio_id != servicio.id_servicio:
            raise serializers.ValidationError(
                {"precio_servicio": "El precio seleccionado no pertenece al servicio indicado."}
            )

        if precio_servicio and modalidad:
            modalidad_precio = (precio_servicio.modalidad or "").strip().upper()
            if modalidad_precio != modalidad:
                raise serializers.ValidationError(
                    {"modalidad": "La modalidad no coincide con la del precio seleccionado."}
                )

        if modalidad == Cita.ModalidadChoices.DOMICILIO:
            if servicio and not servicio.disponible_domicilio:
                raise serializers.ValidationError(
                    {"servicio": "El servicio seleccionado no está disponible a domicilio."}
                )

            direccion = (direccion_cita or "").strip()
            if not direccion and user:
                perfil = getattr(user, "perfil", None)
                direccion = getattr(perfil, "direccion", "") if perfil else ""

            if not direccion:
                raise serializers.ValidationError(
                    {"direccion_cita": "La dirección es obligatoria para citas a domicilio."}
                )

            data["direccion_cita"] = direccion

        if modalidad == Cita.ModalidadChoices.CLINICA:
            data["direccion_cita"] = None

        return data

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["usuario"] = request.user
        return super().create(validated_data)


class CitaEstadoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cita
        fields = ["estado", "motivo_cancelacion", "fecha_confirmacion", "hora_fin"]

    def validate(self, data):
        estado = data.get("estado", getattr(self.instance, "estado", None))
        motivo_cancelacion = data.get("motivo_cancelacion")

        if estado == Cita.EstadoChoices.CANCELADA and not (motivo_cancelacion or "").strip():
            raise serializers.ValidationError(
                {"motivo_cancelacion": "Debes indicar el motivo de cancelación."}
            )

        return data
