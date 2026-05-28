from django.db import models


class DetalleCarritoTemporal(models.Model):
    class TipoItem(models.TextChoices):
        PRODUCTO = "PRODUCTO", "Producto"
        SERVICIO = "SERVICIO", "Servicio"

    id_detalle_carrito = models.AutoField(primary_key=True)
    carrito = models.ForeignKey(
        "GestiondeVentasyPagos.CarritoTemporal",
        db_column="id_carrito",
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    tipo_item = models.CharField(max_length=10, choices=TipoItem.choices)
    producto = models.ForeignKey(
        "GestionInventarioProveedores.Producto",
        db_column="id_producto",
        on_delete=models.PROTECT,
        related_name="detalles_carrito",
        blank=True,
        null=True,
    )
    servicio = models.ForeignKey(
        "GestionServiciosyReserva.Servicio",
        db_column="id_servicio",
        on_delete=models.PROTECT,
        related_name="detalles_carrito",
        blank=True,
        null=True,
    )
    precio_servicio = models.ForeignKey(
        "GestionServiciosyReserva.PrecioServicio",
        db_column="id_precio_servicio",
        on_delete=models.PROTECT,
        related_name="detalles_carrito",
        blank=True,
        null=True,
    )
    mascota = models.ForeignKey(
        "GestionClientesyMascotas.Mascota",
        db_column="id_mascota",
        on_delete=models.PROTECT,
        related_name="detalles_carrito",
        blank=True,
        null=True,
    )
    descripcion_item = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario_estimado = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal_estimado = models.DecimalField(max_digits=12, decimal_places=2)
    observacion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detalle_carrito_temporal"
        verbose_name = "Detalle de carrito temporal"
        verbose_name_plural = "Detalles de carrito temporal"
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name="chk_detail_cart_quantity_gt_zero",
            ),
            models.CheckConstraint(
                check=models.Q(precio_unitario_estimado__gte=0),
                name="chk_detail_cart_unit_price_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(subtotal_estimado__gte=0),
                name="chk_detail_cart_subtotal_non_negative",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        tipo_item="PRODUCTO",
                        producto__isnull=False,
                        servicio__isnull=True,
                        precio_servicio__isnull=True,
                        mascota__isnull=True,
                    )
                    | models.Q(
                        tipo_item="SERVICIO",
                        producto__isnull=True,
                        servicio__isnull=False,
                        precio_servicio__isnull=False,
                        mascota__isnull=False,
                    )
                ),
                name="chk_detail_cart_type_consistency",
            ),
        ]

    def __str__(self):
        return f"{self.tipo_item} x {self.cantidad}"
