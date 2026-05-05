import datetime
from django.db import transaction
from django.utils import timezone
from ..models.historial_clinico import HistorialClinico
from ..models.consulta_clinica import ConsultaClinica
from ..models.receta import Receta
from ..models.detalle_receta import DetalleReceta
from ..models.tratamiento import Tratamiento
from ..models.vacuna_aplicada import VacunaAplicada
from ..models.archivo_clinico import ArchivoClinico

class ClinicaService:
    @staticmethod
    @transaction.atomic
    def registrar_consulta(*, veterinaria_id, mascota_id, veterinario_id, motivo, diagnostico=None, observaciones=None, cita_id=None, peso=None, temperatura=None, f_cardiaca=None, f_respiratoria=None):
        """
        Registra una nueva consulta clínica, asegurando que exista el historial clínico de la mascota.
        """
        # Asegurar historial (id_veterinaria se valida indirectamente por la mascota)
        historial, _ = HistorialClinico.objects.get_or_create(
            mascota_id=mascota_id,
            defaults={'estado': True}
        )

        consulta = ConsultaClinica.objects.create(
            historial_clinico=historial,
            veterinaria_id=veterinaria_id,
            usuario_veterinario_id=veterinario_id,
            cita_id=cita_id,
            motivo_consulta=motivo,
            diagnostico=diagnostico,
            observaciones=observaciones,
            fecha_consulta=timezone.now(),
            peso=peso,
            temperatura=temperatura,
            frecuencia_cardiaca=f_cardiaca,
            frecuencia_respiratoria=f_respiratoria
        )
        return consulta

    @staticmethod
    @transaction.atomic
    def crear_receta(consulta_id, indicaciones, observacion=None):
        return Receta.objects.create(
            consulta_clinica_id=consulta_id,
            fecha=timezone.now(),
            indicaciones=indicaciones,
            observacion=observacion
        )

    @staticmethod
    @transaction.atomic
    def agregar_tratamiento(consulta_id, tipo, descripcion, fecha_ini, fecha_fin=None, observacion=None):
        return Tratamiento.objects.create(
            consulta_clinica_id=consulta_id,
            tipo=tipo,
            descripcion=descripcion,
            fecha_ini=fecha_ini,
            fecha_fin=fecha_fin,
            observacion=observacion
        )

    @staticmethod
    @transaction.atomic
    def registrar_vacuna(consulta_id, nombre_vacuna, dosis, fecha_aplicada, fecha_proxima=None, observacion=None, lote=None, fabricante=None):
        return VacunaAplicada.objects.create(
            consulta_clinica_id=consulta_id,
            nombre_vacuna=nombre_vacuna,
            dosis=dosis,
            fecha_aplicada=fecha_aplicada,
            fecha_proxima=fecha_proxima,
            observacion=observacion,
            lote=lote,
            fabricante=fabricante
        )

    @staticmethod
    @transaction.atomic
    def adjuntar_archivo(consulta_id, nombre, archivo, tipo_archivo):
        return ArchivoClinico.objects.create(
            consulta_clinica_id=consulta_id,
            nombre_archivo=nombre,
            archivo=archivo,
            tipo_archivo=tipo_archivo
        )
