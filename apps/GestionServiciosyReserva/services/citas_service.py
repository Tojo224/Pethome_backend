from django.db import transaction
from rest_framework import serializers
from ..models.citas import Cita
from ..selectors.servicios_selector import CitaSelector

class CitaService:
    @staticmethod
    @transaction.atomic
    def crear_cita(*, veterinaria_id, usuario_id, mascota_id, servicio_id, precio_servicio_id, fecha_programada, hora_inicio, hora_fin, modalidad, direccion_cita=None, descripcion=None):
        """
        Crea una cita validando que no haya conflictos de horario (solapamientos).
        """
        if CitaSelector.verificar_conflicto_horario(veterinaria_id, fecha_programada, hora_inicio, hora_fin):
            raise serializers.ValidationError({
                "detail": "El horario seleccionado ya está ocupado por otra cita activa.",
                "code": "CONFLICTO_HORARIO"
            })

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
            estado="PENDIENTE"
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
        if CitaSelector.verificar_conflicto_horario(cita.veterinaria_id, nueva_fecha, nueva_hora_inicio, nueva_hora_fin, excluir_cita_id=cita.pk):
            raise serializers.ValidationError({
                "detail": "El nuevo horario solicitado ya está ocupado.",
                "code": "CONFLICTO_HORARIO"
            })
        
        cita.fecha_programada = nueva_fecha
        cita.hora_inicio = nueva_hora_inicio
        cita.hora_fin = nueva_hora_fin
        cita.save()
        return cita
