from django.utils import timezone
from rest_framework import serializers
from datetime import datetime, timedelta

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
            "hora_fin",  # se calcula automáticamente
            "estado",
            "motivo_cancelacion",
        ]

    def validate(self, data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        tenant = getattr(request, "tenant", None) if request else None
        tenant_id = getattr(tenant, "id", None)

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
        fecha_programada = data.get(
            "fecha_programada",
            getattr(self.instance, "fecha_programada", None),
        )
        hora_inicio = data.get("hora_inicio", getattr(self.instance, "hora_inicio", None))

        # ---------------- VALIDACIONES TENANT ----------------

        if tenant_id is None:
            raise serializers.ValidationError(
                "No se pudo resolver el tenant activo."
            )

        if mascota and mascota.veterinaria_id != tenant_id:
            raise serializers.ValidationError(
                {"mascota": "La mascota no pertenece a la veterinaria actual."}
            )

        if servicio and servicio.veterinaria_id != tenant_id:
            raise serializers.ValidationError(
                {"servicio": "El servicio no pertenece a la veterinaria actual."}
            )

        if precio_servicio and precio_servicio.veterinaria_id != tenant_id:
            raise serializers.ValidationError(
                {"precio_servicio": "El precio no pertenece a la veterinaria actual."}
            )

        # ---------------- VALIDACIONES EXISTENTES ----------------

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

        if fecha_programada and hora_inicio:
            fecha_hora_programada = timezone.datetime.combine(
                fecha_programada,
                hora_inicio,
            )
            fecha_hora_programada = timezone.make_aware(
                fecha_hora_programada,
                timezone.get_current_timezone(),
            )

            if fecha_hora_programada <= timezone.localtime():
                raise serializers.ValidationError(
                    {"fecha_programada": "La fecha y hora de la cita deben ser futuras."}
                )

        # ---------------- VALIDACIÓN DE MODALIDAD ----------------

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

        # ---------------- VALIDACIÓN DE HORARIO ----------------

        HORA_APERTURA = 8
        HORA_CIERRE = 18

        if hora_inicio:
            if hora_inicio.hour < HORA_APERTURA or hora_inicio.hour >= HORA_CIERRE:
                raise serializers.ValidationError({
                    "hora_inicio": f"Horario permitido: {HORA_APERTURA}:00 - {HORA_CIERRE}:00"
                })

        # ---------------- VALIDACIÓN DE CHOQUES ----------------

        if fecha_programada and hora_inicio:

            inicio = datetime.combine(fecha_programada, hora_inicio)

            # calcular hora_fin automáticamente
            if servicio and servicio.duracion_estimada:
                fin = inicio + timedelta(minutes=servicio.duracion_estimada)
                data["hora_fin"] = fin.time()
            else:
                hora_fin = data.get("hora_fin") or getattr(self.instance, "hora_fin", None)
                if not hora_fin:
                    raise serializers.ValidationError({
                        "hora_fin": "Debe especificar hora_fin o configurar duración del servicio"
                    })
                fin = datetime.combine(fecha_programada, hora_fin)

            if inicio >= fin:
                raise serializers.ValidationError(
                    {"hora_inicio": "La hora fin debe ser mayor a la hora inicio"}
                )

            #  filtrar por modalidad 
            citas = Cita.objects.filter(
                fecha_programada=fecha_programada,
                modalidad=modalidad,
                veterinaria_id=tenant_id,
                estado__in=[
                    Cita.EstadoChoices.PENDIENTE,
                    Cita.EstadoChoices.CONFIRMADA,
                ],
            )

            # excluir si es edición
            if self.instance:
                citas = citas.exclude(id_cita=self.instance.id_cita)

            for cita in citas:
                inicio_db = datetime.combine(cita.fecha_programada, cita.hora_inicio)
                fin_db = datetime.combine(cita.fecha_programada, cita.hora_fin)

                if inicio < fin_db and fin > inicio_db:
                    raise serializers.ValidationError({
                         "Ya existe una cita en ese horario para esta modalidad"
                    })

        return data

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["usuario"] = request.user
        return super().create(validated_data)


class CitaEstadoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cita
        fields = [
            "estado",
            "motivo_cancelacion",
            "fecha_confirmacion",
            "fecha_programada",
            "hora_inicio",
            "hora_fin",
        ]

    def validate(self, data):
        estado_actual = getattr(self.instance, "estado", None)
        estado = data.get("estado", estado_actual)
        motivo_cancelacion = data.get("motivo_cancelacion")
        fecha_programada = data.get("fecha_programada", getattr(self.instance, "fecha_programada", None))
        hora_inicio = data.get("hora_inicio", getattr(self.instance, "hora_inicio", None))

        if estado == Cita.EstadoChoices.CANCELADA and not (motivo_cancelacion or "").strip():
            raise serializers.ValidationError(
                {"Debes indicar el motivo de cancelación."}
            )

        # No permitir cambiar citas completadas/canceladas a otros estados desde móvil cliente.
        if estado_actual in {Cita.EstadoChoices.CANCELADA, Cita.EstadoChoices.COMPLETADA} and estado != estado_actual:
            raise serializers.ValidationError(
                {"estado": "No se puede modificar una reserva cancelada o completada."}
            )

        # Si se reprograma (fecha/hora), debe ser futura.
        if fecha_programada and hora_inicio:
            dt = timezone.datetime.combine(fecha_programada, hora_inicio)
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
            if dt <= timezone.localtime():
                raise serializers.ValidationError(
                    {"fecha_programada": "La nueva fecha y hora deben ser futuras."}
                )

        return data
