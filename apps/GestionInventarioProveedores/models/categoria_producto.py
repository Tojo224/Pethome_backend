from django.db import models


class CategoriaProducto(models.Model):
    id_categoria_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="categorias_producto",
        null=False,
        blank=False,
    )

    class Meta:
        db_table = "categoria_producto"
        verbose_name = "Categoría de producto"
        verbose_name_plural = "Categorías de producto"
        constraints = [
            models.UniqueConstraint(
                fields=["veterinaria", "nombre"],
                name="uq_categoria_producto_veterinaria_nombre",
            )
        ]

    def __str__(self):
        return self.nombre
