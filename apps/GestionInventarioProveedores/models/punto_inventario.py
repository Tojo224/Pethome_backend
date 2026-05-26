from django.db import models


class PuntoInventario(models.Model):
    class TipoPunto(models.TextChoices):
        ALMACEN_GENERAL = "ALMACEN_GENERAL", "Almacen general"
        SUCURSAL = "SUCURSAL", "Sucursal"
        UNIDAD_MOVIL = "UNIDAD_MOVIL", "Unidad movil"

    id_punto = models.AutoField(primary_key=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="puntos_inventario",
    )
    tipo = models.CharField(max_length=20, choices=TipoPunto.choices)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "punto_inventario"
        verbose_name = "Punto de inventario"
        verbose_name_plural = "Puntos de inventario"
        constraints = [
            models.UniqueConstraint(
                fields=["veterinaria", "tipo", "nombre"],
                name="uq_punto_inventario_veterinaria_tipo_nombre",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"
