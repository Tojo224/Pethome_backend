from django.db.models import Q
from ..models.servicios import Servicio
from ..models.categoriaservicio import CategoriaServicio
from ..models.precioservicio import PrecioServicio
from ..models.citas import Cita

class ServicioSelector:
    @staticmethod
    def get_servicios_by_tenant(veterinaria_id, solo_activos=False):
        queryset = Servicio.objects.filter(veterinaria_id=veterinaria_id).select_related("categoria")
        if solo_activos:
            queryset = queryset.filter(estado=True)
        return queryset

    @staticmethod
    def get_servicio_detail(pk, veterinaria_id):
        return Servicio.objects.filter(pk=pk, veterinaria_id=veterinaria_id).first()

class CategoriaSelector:
    @staticmethod
    def get_categorias_by_tenant(veterinaria_id):
        return CategoriaServicio.objects.filter(veterinaria_id=veterinaria_id)

class PrecioServicioSelector:
    @staticmethod
    def get_precios_by_tenant(veterinaria_id):
        return PrecioServicio.objects.filter(veterinaria_id=veterinaria_id).select_related("servicio")

class CitaSelector:
    ESTADOS_ACTIVOS = [
        Cita.EstadoChoices.PENDIENTE,
        Cita.EstadoChoices.CONFIRMADA,
    ]

    @staticmethod
    def get_citas_by_tenant(veterinaria_id, user=None):
        queryset = Cita.objects.filter(veterinaria_id=veterinaria_id).select_related(
            "usuario", "mascota", "servicio", "precio_servicio"
        )
        if user and hasattr(user, "role") and user.role.nombre == "CLIENT":
            queryset = queryset.filter(usuario=user)
        return queryset

    @staticmethod
    def get_citas_by_fecha(veterinaria_id, fecha):
        return Cita.objects.filter(
            veterinaria_id=veterinaria_id,
            fecha_programada=fecha,
            estado__in=CitaSelector.ESTADOS_ACTIVOS,
        ).select_related("mascota", "servicio", "usuario")

    @staticmethod
    def verificar_conflicto_horario(veterinaria_id, fecha, hora_inicio, hora_fin, excluir_cita_id=None):
        """
        Verifica si existe solapamiento de horarios.
        Lógica: Una cita choca si (Inicio < Fin_Existente) Y (Fin > Inicio_Existente)
        """
        queryset = Cita.objects.filter(
            veterinaria_id=veterinaria_id,
            fecha_programada=fecha,
            estado__in=CitaSelector.ESTADOS_ACTIVOS,
        )

        if excluir_cita_id:
            queryset = queryset.exclude(id_cita=excluir_cita_id)

        return queryset.filter(
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio
        ).exists()

    @staticmethod
    def get_cita_detail(pk, veterinaria_id):
        return Cita.objects.filter(pk=pk, veterinaria_id=veterinaria_id).select_related(
            "usuario", "mascota", "servicio", "precio_servicio"
        ).first()

    @staticmethod
    def check_conflicto_horario(veterinaria_id, fecha, hora, exclude_id=None):
        """Verifica si existe una cita en el mismo horario para la veterinaria."""
        queryset = Cita.objects.filter(
            veterinaria_id=veterinaria_id,
            fecha=fecha,
            hora=hora
        ).exclude(estado="CANCELADA")
        
        if exclude_id:
            queryset = queryset.exclude(pk=exclude_id)
            
        return queryset.exists()
