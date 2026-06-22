from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PlanSanitarioPreventivo(models.Model):
    class TipoEventoChoices(models.TextChoices):
        CONTROL = "CONTROL", "Control"
        VACUNA = "VACUNA", "Vacuna"
        DESPARASITACION = "DESPARASITACION", "Desparasitación"
        REVISION = "REVISION", "Revisión"
        OTRO = "OTRO", "Otro"

    class EstadoPlanChoices(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        REALIZADO = "REALIZADO", "Realizado"
        VENCIDO = "VENCIDO", "Vencido"
        CANCELADO = "CANCELADO", "Cancelado"

    id_plan_sanitario = models.AutoField(primary_key=True)
    mascota = models.ForeignKey(
        "GestionClientesyMascotas.Mascota",
        db_column="id_mascota",
        on_delete=models.CASCADE,
        related_name="planes_sanitarios_preventivos",
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="planes_sanitarios_preventivos",
    )
    usuario_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_usuario_registro",
        on_delete=models.PROTECT,
        related_name="planes_sanitarios_registrados",
    )
    tipo_evento = models.CharField(
        max_length=20,
        choices=TipoEventoChoices.choices,
    )
    descripcion = models.CharField(max_length=255)
    fecha_programada = models.DateField()
    estado_plan = models.CharField(
        max_length=15,
        choices=EstadoPlanChoices.choices,
        default=EstadoPlanChoices.PENDIENTE,
    )
    observaciones = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plan_sanitario_preventivo"
        verbose_name = "Plan sanitario preventivo"
        verbose_name_plural = "Planes sanitarios preventivos"
        ordering = ["fecha_programada", "-fecha_creacion"]

    def __str__(self):
        return f"{self.mascota.nombre} - {self.tipo_evento} - {self.fecha_programada}"

    def clean(self):
        super().clean()

        if not self.fecha_programada or not self.estado_plan:
            return

        hoy = timezone.localdate()

        if (
            self.estado_plan == self.EstadoPlanChoices.PENDIENTE
            and self.fecha_programada < hoy
        ):
            raise ValidationError(
                {
                    "estado_plan": "No se puede programar un evento pendiente en una fecha pasada."
                }
            )

        if (
            self.estado_plan == self.EstadoPlanChoices.VENCIDO
            and self.fecha_programada >= hoy
        ):
            raise ValidationError(
                {
                    "estado_plan": "No se puede marcar como vencido un evento cuya fecha aún no ha pasado."
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
