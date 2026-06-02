from django.conf import settings
from django.db import models


class ReporteGenerado(models.Model):
    class OrigenChoices(models.TextChoices):
        ESTATICO = "ESTATICO", "Estático"
        DINAMICO = "DINAMICO", "Dinámico"

    class FormatoChoices(models.TextChoices):
        PDF = "PDF", "PDF"
        EXCEL = "EXCEL", "Excel"
        HTML = "HTML", "HTML"

    class EstadoChoices(models.TextChoices):
        GENERADO = "GENERADO", "Generado"
        ERROR = "ERROR", "Error"

    id_reporte = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_usuario",
        on_delete=models.SET_NULL,
        related_name="reportes_generados",
        null=True,
        blank=True,
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.SET_NULL,
        related_name="reportes_generados",
        null=True,
        blank=True,
    )
    tipo_reporte = models.CharField(max_length=100)
    origen = models.CharField(max_length=20, choices=OrigenChoices.choices)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(null=True, blank=True)
    filtros = models.JSONField(null=True, blank=True)
    columnas = models.JSONField(null=True, blank=True)
    datos = models.JSONField(null=True, blank=True)
    formato = models.CharField(max_length=10, choices=FormatoChoices.choices)
    estado = models.CharField(max_length=20, choices=EstadoChoices.choices)
    mensaje_error = models.TextField(null=True, blank=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "reporte_generado"
        verbose_name = "Reporte Generado"
        verbose_name_plural = "Reportes Generados"

    def __str__(self):
        return f"Reporte {self.titulo} ({self.id_reporte})"
