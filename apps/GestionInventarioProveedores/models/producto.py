from django.db import models


class Producto(models.Model):
    class TipoMascota(models.TextChoices):
        PERRO = "PERRO", "Perro"
        GATO = "GATO", "Gato"
        AVE = "AVE", "Ave"
        ROEDOR = "ROEDOR", "Roedor"
        PEZ = "PEZ", "Pez"
        OTRO = "OTRO", "Otro"

    class TipoDescuento(models.TextChoices):
        PORCENTAJE = "PORCENTAJE", "Porcentaje"
        MONTO_FIJO = "MONTO_FIJO", "Monto fijo"
        PRECIO_ESPECIAL = "PRECIO_ESPECIAL", "Precio especial"

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

    tipo_mascota = models.CharField(
        max_length=20,
        choices=TipoMascota.choices,
        blank=True,
        null=True,
    )

    destacado = models.BooleanField(default=False)

    novedad_desde = models.DateField(blank=True, null=True)
    novedad_hasta = models.DateField(blank=True, null=True)

    tiene_promocion = models.BooleanField(default=False)
    tipo_descuento = models.CharField(
        max_length=20,
        choices=TipoDescuento.choices,
        blank=True,
        null=True,
    )
    porcentaje_descuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
    )
    monto_descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    precio_promocional = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    promocion_fecha_inicio = models.DateField(blank=True, null=True)
    promocion_fecha_fin = models.DateField(blank=True, null=True)

    # Control de vencimiento
    requiere_control_vencimiento = models.BooleanField(
        default=False,
        help_text="Indica si el producto requiere control de fecha de vencimiento"
    )
    dias_alerta_vencimiento = models.IntegerField(
        default=30,
        help_text="Días de anticipación para alertar sobre vencimiento próximo"
    )

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
        constraints = [
            models.UniqueConstraint(
                fields=["veterinaria", "nombre", "categoria_producto"],
                name="uq_producto_veterinaria_nombre_categoria",
            )
        ]

    def __str__(self):
        return self.nombre
