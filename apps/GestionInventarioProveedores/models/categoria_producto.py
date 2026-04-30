from django.db import models


class CategoriaProducto(models.Model):
    id_categoria_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "categoria_producto"
        verbose_name = "Categoría de producto"
        verbose_name_plural = "Categorías de producto"

    def __str__(self):
        return self.nombre