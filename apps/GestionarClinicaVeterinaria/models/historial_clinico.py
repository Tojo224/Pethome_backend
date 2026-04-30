from django.db import models


class HistorialClinico(models.Model):
    id_historial_clinico = models.AutoField(primary_key=True)
    mascota = models.OneToOneField(
        "GestionClientesyMascotas.Mascota",
        db_column="id_mascota",
        on_delete=models.CASCADE,
        related_name="historial_clinico",
    )
    observaciones_generales = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "historial_clinico"
        verbose_name = "Historial clínico"
        verbose_name_plural = "Historiales clínicos"

    def __str__(self):
        return f"Historial clínico - {self.mascota.nombre}"