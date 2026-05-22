from django.db import models


class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)

    categoria_producto = models.ForeignKey(
        "GestionInventarioProveedores.CategoriaProducto",
        db_column="id_categoria_producto",
        on_delete=models.PROTECT,
        related_name="productos",
    )

    proveedor = models.ForeignKey(
        "GestionInventarioProveedores.Proveedor",
        db_column="id_proveedor",
        on_delete=models.SET_NULL,
        related_name="productos",
        blank=True,
        null=True,
    )

    nombre = models.CharField(max_length=150)

    descripcion = models.TextField(blank=True, null=True)

    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )

    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )

    unidad_medida = models.CharField(max_length=50, blank=True, null=True)

    imagen = models.ImageField(
        upload_to="productos/",
        blank=True,
        null=True,
    )

    visible_catalogo = models.BooleanField(default=True)

    estado = models.BooleanField(default=True)

    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="productos",
        null=False,
        blank=False,
    )

    class Meta:
        db_table = "producto"
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return self.nombre