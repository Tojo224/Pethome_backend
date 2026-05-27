from django.db import models


class DetalleVenta(models.Model):
    class TipoItem(models.TextChoices):
        PRODUCTO = "PRODUCTO", "Producto"
        SERVICIO = "SERVICIO", "Servicio"

    id_detalle_venta = models.AutoField(primary_key=True)
    venta = models.ForeignKey(
        "GestiondeVentasyPagos.Venta",
        db_column="id_venta",
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    tipo_item = models.CharField(max_length=10, choices=TipoItem.choices)
    producto = models.ForeignKey(
        "GestionInventarioProveedores.Producto",
        db_column="id_producto",
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        blank=True,
        null=True,
    )
    servicio = models.ForeignKey(
        "GestionServiciosyReserva.Servicio",
        db_column="id_servicio",
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        blank=True,
        null=True,
    )
    precio_servicio = models.ForeignKey(
        "GestionServiciosyReserva.PrecioServicio",
        db_column="id_precio_servicio",
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        blank=True,
        null=True,
    )
    descripcion_item = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    observacion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detalle_venta"
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name="chk_detalle_venta_cantidad_mayor_cero",
            ),
            models.CheckConstraint(
                check=models.Q(precio_unitario__gt=0),
                name="chk_detalle_venta_precio_mayor_cero",
            ),
            models.CheckConstraint(
                check=models.Q(subtotal__gte=0),
                name="chk_detalle_venta_subtotal_no_negativo",
            ),
        ]

    def __str__(self):
        return f"{self.tipo_item} x {self.cantidad}"
