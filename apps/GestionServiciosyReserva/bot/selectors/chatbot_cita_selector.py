from apps.AutenticacionySeguridad.enums.roles import RoleEnum

from ...models.citas import Cita


class ChatbotCitaSelector:
    @staticmethod
    def listar_citas_usuario(*, user, veterinaria_id):
        """
        Lista citas dentro del tenant actual.

        Si el usuario es CLIENT, solo devuelve sus propias citas.
        Si es admin/recepciAn/veterinario, devuelve citas del tenant.
        """

        qs = Cita.objects.select_related(
            "mascota",
            "servicio",
            "precio_servicio",
            "usuario",
        ).filter(
            veterinaria_id=veterinaria_id,
        )

        role_name = getattr(getattr(user, "role", None), "nombre", "")

        if role_name == RoleEnum.CLIENT.value:
            qs = qs.filter(usuario_id=user.id_usuario)

        return qs.order_by("-fecha_programada", "-hora_inicio", "-id_cita")

    @staticmethod
    def listar_citas_activas_usuario(*, user, veterinaria_id):
        """
        Lista citas que todavAa pueden ser canceladas o reprogramadas.
        """

        return ChatbotCitaSelector.listar_citas_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
        ).filter(
            estado__in=[
                Cita.EstadoChoices.PENDIENTE,
                Cita.EstadoChoices.CONFIRMADA,
            ]
        )

    @staticmethod
    def obtener_cita_usuario(*, user, veterinaria_id, id_cita):
        """
        Obtiene una cita especAfica respetando tenant y usuario.
        """

        qs = ChatbotCitaSelector.listar_citas_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
        ).filter(id_cita=id_cita)

        return qs.first()

    @staticmethod
    def to_option(cita):
        mascota_nombre = None
        servicio_nombre = None

        if getattr(cita, "mascota", None):
            mascota_nombre = getattr(cita.mascota, "nombre", None)

        if getattr(cita, "servicio", None):
            servicio_nombre = getattr(cita.servicio, "nombre", None)

        return {
            "id_cita": cita.id_cita,
            "mascota": cita.mascota_id,
            "mascota_nombre": mascota_nombre,
            "servicio": cita.servicio_id,
            "servicio_nombre": servicio_nombre,
            "fecha_programada": cita.fecha_programada.isoformat() if cita.fecha_programada else None,
            "hora_inicio": cita.hora_inicio.strftime("%H:%M:%S") if cita.hora_inicio else None,
            "hora_fin": cita.hora_fin.strftime("%H:%M:%S") if cita.hora_fin else None,
            "modalidad": cita.modalidad,
            "estado": cita.estado,
            "motivo_cancelacion": cita.motivo_cancelacion,
        }