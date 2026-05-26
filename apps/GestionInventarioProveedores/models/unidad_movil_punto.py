from django.db import models


class UnidadMovilPunto(models.Model):
    id_unidad_movil_punto = models.AutoField(primary_key=True)
    unidad_movil = models.OneToOneField(
        "GestionServiciosyReserva.UnidadMovil",
        db_column="id_unidad",
        on_delete=models.CASCADE,
        related_name="inventario_punto",
    )
    punto_inventario = models.OneToOneField(
        "GestionInventarioProveedores.PuntoInventario",
        db_column="id_punto",
        on_delete=models.CASCADE,
        related_name="unidad_movil_link",
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="unidades_moviles_punto",
    )
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "unidad_movil_punto"
        verbose_name = "Vinculo unidad movil punto inventario"
        verbose_name_plural = "Vinculos unidad movil punto inventario"

    def __str__(self):
        return f"Unidad {self.unidad_movil_id} -> Punto {self.punto_inventario_id}"
