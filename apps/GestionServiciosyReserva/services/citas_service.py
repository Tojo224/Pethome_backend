from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from ..models.citas import Cita
from ..selectors.servicios_selector import CitaSelector


class CitaService:
    @staticmethod
    @transaction.atomic
    def cancelar_vencidas_por_tenant(veterinaria_id):
        """
        Cancela automaticamente citas PENDIENTE/CONFIRMADA cuya fecha/hora ya paso.
        Acotado por tenant para respetar aislamiento multitenant.
        """
        ahora = timezone.localtime()
        hoy = ahora.date()
        hora_actual = ahora.time()

        qs = Cita.objects.filter(
            veterinaria_id=veterinaria_id,
            estado__in=[Cita.EstadoChoices.PENDIENTE, Cita.EstadoChoices.CONFIRMADA],
        ).filter(
            Q(fecha_programada__lt=hoy)
            | (Q(fecha_programada=hoy) & Q(hora_inicio__lt=hora_actual))
        )

        return qs.update(
            estado=Cita.EstadoChoices.CANCELADA,
            motivo_cancelacion="Cancelacion automatica por vencimiento de fecha/hora.",
        )

    @staticmethod
    @transaction.atomic
    def crear_cita(
        *,
        veterinaria_id,
        usuario_id,
        mascota_id,
        servicio_id,
        precio_servicio_id,
        fecha_programada,
        hora_inicio,
        hora_fin,
        modalidad,
        direccion_cita=None,
        descripcion=None,
    ):
        """
        Crea una cita validando que no haya conflictos de horario (solapamientos).
        """
        if CitaSelector.verificar_conflicto_horario(
            veterinaria_id,
            fecha_programada,
            hora_inicio,
            hora_fin,
        ):
            raise serializers.ValidationError(
                {
                    "detail": "El horario seleccionado ya esta ocupado por otra cita activa.",
                    "code": "CONFLICTO_HORARIO",
                }
            )

        cita = Cita.objects.create(
            veterinaria_id=veterinaria_id,
            usuario_id=usuario_id,
            mascota_id=mascota_id,
            servicio_id=servicio_id,
            precio_servicio_id=precio_servicio_id,
            fecha_programada=fecha_programada,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            modalidad=modalidad,
            direccion_cita=direccion_cita,
            descripcion=descripcion,
            estado="PENDIENTE",
        )
        return cita

    @staticmethod
    @transaction.atomic
    def actualizar_estado(cita, nuevo_estado, motivo_cancelacion=None):
        cita.estado = nuevo_estado
        if motivo_cancelacion:
            cita.motivo_cancelacion = motivo_cancelacion
        cita.save()
        return cita

    @staticmethod
    @transaction.atomic
    def reprogramar_cita(cita, nueva_fecha, nueva_hora_inicio, nueva_hora_fin):
        # If hora_fin is missing from frontend, try to compute it from service duration.
        if (
            nueva_hora_fin is None
            and getattr(cita, "servicio", None)
            and cita.servicio.duracion_estimada
        ):
            inicio_dt = datetime.combine(nueva_fecha, nueva_hora_inicio)
            nueva_hora_fin = (
                inicio_dt + timedelta(minutes=cita.servicio.duracion_estimada)
            ).time()

        # Fallback to current booking end time.
        if nueva_hora_fin is None:
            nueva_hora_fin = cita.hora_fin

        if nueva_hora_fin is None:
            raise serializers.ValidationError(
                {
                    "hora_fin": "No se pudo determinar la hora fin para reprogramar la reserva."
                }
            )

        if CitaSelector.verificar_conflicto_horario(
            cita.veterinaria_id,
            nueva_fecha,
            nueva_hora_inicio,
            nueva_hora_fin,
            excluir_cita_id=cita.pk,
        ):
            raise serializers.ValidationError(
                {
                    "detail": "El nuevo horario solicitado ya esta ocupado.",
                    "code": "CONFLICTO_HORARIO",
                }
            )

        cita.fecha_programada = nueva_fecha
        cita.hora_inicio = nueva_hora_inicio
        cita.hora_fin = nueva_hora_fin
        cita.save()
        return cita
