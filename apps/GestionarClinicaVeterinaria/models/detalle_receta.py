from django.db import models


class DetalleReceta(models.Model):
    id_detalle_receta = models.AutoField(primary_key=True)
    receta = models.ForeignKey(
        "GestionarClinicaVeterinaria.Receta",
        db_column="id_receta",
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "GestionInventarioProveedores.Producto",
        db_column="id_producto",
        on_delete=models.SET_NULL,
        related_name="detalles_receta",
        blank=True,
        null=True,
    )
    medicamento = models.CharField(max_length=150)
    dosis = models.CharField(max_length=100)
    frecuencia = models.CharField(max_length=100)
    duracion_dias = models.PositiveIntegerField()
    indicaciones_adicionales = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "detalle_receta"
        verbose_name = "Detalle de receta"
        verbose_name_plural = "Detalles de receta"

    def __str__(self):
        return f"{self.medicamento} - {self.dosis}"