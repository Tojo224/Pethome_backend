from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.GestionServiciosyReserva.models.citas import Cita
from apps.NotificacionesySeguimiento.services.notification_service import NotificationService
from apps.NotificacionesySeguimiento.models import Notificacion

@receiver(post_save, sender=Cita)
def notificar_cambios_cita(sender, instance, created, **kwargs):
    """
    Dispara notificaciones automáticas cuando se crea o actualiza una cita.
    """
    usuario_cliente = instance.usuario
    veterinaria_nombre = instance.veterinaria.nombre
    id_cita = instance.id_cita

    if created:
        # 1. Notificar al Cliente sobre su nueva reserva
        NotificationService.notify_user(
            user=usuario_cliente,
            title="Nueva Reserva Programada",
            message=f"Tu reserva para {instance.servicio.nombre} en {veterinaria_nombre} ha sido creada para el {instance.fecha_programada} a las {instance.hora_inicio}.",
            tipo=Notificacion.TipoNotificacion.RESERVA,
            id_entidad=id_cita,
            link=f"/dashboard/citas/{id_cita}"
        )
        # 2. Notificar al Administrador de la veterinaria
        NotificationService.notify_veterinaria(
            veterinaria=instance.veterinaria,
            title="🔔 Nueva Cita Recibida",
            message=f"El cliente {usuario_cliente.correo} ha agendado una cita para {instance.mascota.nombre} el {instance.fecha_programada}.",
            link=f"/dashboard/agenda"
        )
    else:
        # 2. Notificar cambios de estado
        if instance.estado == Cita.EstadoChoices.CONFIRMADA:
            NotificationService.notify_user(
                user=usuario_cliente,
                title="Reserva Confirmada",
                message=f"Tu cita en {veterinaria_nombre} ha sido confirmada. ¡Te esperamos!",
                tipo=Notificacion.TipoNotificacion.RESERVA,
                id_entidad=id_cita,
                link=f"/dashboard/citas/{id_cita}"
            )
        elif instance.estado == Cita.EstadoChoices.CANCELADA:
            NotificationService.notify_user(
                user=usuario_cliente,
                title="Reserva Cancelada",
                message=f"Tu cita para {instance.servicio.nombre} en {veterinaria_nombre} ha sido cancelada.",
                tipo=Notificacion.TipoNotificacion.RESERVA,
                id_entidad=id_cita,
                link=f"/dashboard/citas/{id_cita}"
            )
