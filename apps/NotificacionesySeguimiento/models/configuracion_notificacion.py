from django.db import models
from apps.AutenticacionySeguridad.models.veterinaria import Veterinaria

class ConfiguracionNotificacion(models.Model):
    class TipoNotificacion(models.TextChoices):
        RESERVA = "RESERVA", "Reserva de Cita"
        VACUNA = "VACUNA", "Recordatorio de Vacuna"
        CONTROL = "CONTROL", "Control Clínico"

    id_configuracion = models.AutoField(primary_key=True)
    veterinaria = models.ForeignKey(
        Veterinaria,
        on_delete=models.CASCADE,
        db_column="id_veterinaria",
        related_name="configuraciones_notificacion"
    )
    tipo_notificacion = models.CharField(
        max_length=20,
        choices=TipoNotificacion.choices
    )
    dias_anticipacion = models.IntegerField(default=1)
    canales_habilitados = models.JSONField(
        default=dict,
        help_text="Ej: {'email': true, 'push': true, 'web': true}"
    )
    activo = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "configuracion_notificacion"
        verbose_name = "Configuración de Notificación"
        verbose_name_plural = "Configuraciones de Notificación"
        unique_together = ("veterinaria", "tipo_notificacion")

    def __str__(self):
        return f"{self.veterinaria.nombre} - {self.get_tipo_notificacion_display()}"
