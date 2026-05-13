from django.db import models
from django.conf import settings
from apps.AutenticacionySeguridad.models.veterinaria import Veterinaria

class Notificacion(models.Model):
    class EstadoNotificacion(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ENVIADA = "ENVIADA", "Enviada"
        LEIDA = "LEIDA", "Leída"
        FALLIDA = "FALLIDA", "Fallida"
        CANCELADA = "CANCELADA", "Cancelada"

    class TipoNotificacion(models.TextChoices):
        RESERVA = "RESERVA", "Reserva"
        VACUNA = "VACUNA", "Vacuna"
        CONTROL = "CONTROL", "Control Clínico"
        SISTEMA = "SISTEMA", "Sistema"

    id_notificacion = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="id_usuario",
        related_name="notificaciones"
    )
    veterinaria = models.ForeignKey(
        Veterinaria,
        on_delete=models.CASCADE,
        db_column="id_veterinaria",
        related_name="notificaciones"
    )
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    tipo = models.CharField(
        max_length=20,
        choices=TipoNotificacion.choices,
        default=TipoNotificacion.SISTEMA
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoNotificacion.choices,
        default=EstadoNotificacion.PENDIENTE
    )
    id_entidad_relacionada = models.IntegerField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_leida = models.DateTimeField(null=True, blank=True)
    link = models.URLField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "notificacion"
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.titulo} - {self.usuario.correo}"
