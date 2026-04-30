from django.conf import settings
from django.db import models


class ConsultaClinica(models.Model):
    id_consulta_clinica = models.AutoField(primary_key=True)

    historial_clinico = models.ForeignKey(
        "GestionarClinicaVeterinaria.HistorialClinico",
        db_column="id_historial_clinico",
        on_delete=models.CASCADE,
        related_name="consultas_clinicas",
    )

    cita = models.ForeignKey(
        "GestionServiciosyReserva.Cita",
        db_column="id_cita",
        on_delete=models.SET_NULL,
        related_name="consultas_clinicas",
        blank=True,
        null=True,
    )

    usuario_veterinario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_usuario_veterinario",
        on_delete=models.PROTECT,
        related_name="consultas_veterinarias",
    )

    motivo_consulta = models.TextField()
    diagnostico = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    fecha_consulta = models.DateTimeField()

    peso = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    temperatura = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    frecuencia_cardiaca = models.PositiveIntegerField(blank=True, null=True)
    frecuencia_respiratoria = models.PositiveIntegerField(blank=True, null=True)
    proxima_revision = models.DateTimeField(blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "consulta_clinica"
        verbose_name = "Consulta clínica"
        verbose_name_plural = "Consultas clínicas"
        ordering = ["-fecha_consulta"]

    def __str__(self):
        return f"Consulta #{self.id_consulta_clinica}"