from ..models.historial_clinico import HistorialClinico
from ..models.consulta_clinica import ConsultaClinica
from ..models.receta import Receta
from ..models.tratamiento import Tratamiento
from ..models.vacuna_aplicada import VacunaAplicada

class HistorialClinicoSelector:
    @staticmethod
    def get_historial_by_mascota(mascota_id, veterinaria_id):
        return HistorialClinico.objects.filter(
            mascota_id=mascota_id,
            mascota__veterinaria_id=veterinaria_id
        ).select_related("mascota").first()

    @staticmethod
    def get_historiales_by_tenant(veterinaria_id):
        return HistorialClinico.objects.filter(
            mascota__veterinaria_id=veterinaria_id
        ).select_related("mascota")

class ConsultaClinicaSelector:
    @staticmethod
    def get_consultas_by_historial(historial_id, veterinaria_id):
        return ConsultaClinica.objects.filter(
            historial_clinico_id=historial_id,
            veterinaria_id=veterinaria_id
        ).select_related("usuario_veterinario", "cita").order_by("-fecha_consulta")

    @staticmethod
    def get_consulta_detail(pk, veterinaria_id):
        return ConsultaClinica.objects.filter(
            pk=pk,
            veterinaria_id=veterinaria_id
        ).select_related("usuario_veterinario", "cita", "historial_clinico").first()

class RecetaSelector:
    @staticmethod
    def get_recetas_by_consulta(consulta_id, veterinaria_id):
        return Receta.objects.filter(
            consulta_id=consulta_id,
            veterinaria_id=veterinaria_id
        ).prefetch_related("detalles")

class TratamientoSelector:
    @staticmethod
    def get_tratamientos_by_consulta(consulta_id, veterinaria_id):
        return Tratamiento.objects.filter(
            consulta_id=consulta_id,
            veterinaria_id=veterinaria_id
        )

class VacunaSelector:
    @staticmethod
    def get_vacunas_by_mascota(mascota_id, veterinaria_id):
        return VacunaAplicada.objects.filter(
            consulta_clinica__historial_clinico__mascota_id=mascota_id,
            consulta_clinica__veterinaria_id=veterinaria_id
        ).select_related("usuario_veterinario").order_by("-fecha_aplicacion")
