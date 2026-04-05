from django.db import models
from .servicios import Servicio

class PrecioServicio(models.Model):
    id_precio = models.AutoField(primary_key=True)

    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name="precios"
    )

    variacion = models.CharField(max_length=50, default="General")
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "precios_servicio"
        verbose_name = "Precio de Servicio"
        verbose_name_plural = "Precios de Servicio"

    def __str__(self):
        return f"{self.servicio.nombre} - {self.variacion}"