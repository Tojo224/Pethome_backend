from django.db import models


class StockPunto(models.Model):
    id_stock = models.AutoField(primary_key=True)
    punto_inventario = models.ForeignKey(
        "GestionInventarioProveedores.PuntoInventario",
        db_column="id_punto",
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    producto = models.ForeignKey(
        "GestionInventarioProveedores.Producto",
        db_column="id_producto",
        on_delete=models.PROTECT,
        related_name="stocks_por_punto",
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="stocks_punto",
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cantidad_minima = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_punto"
        verbose_name = "Stock por punto"
        verbose_name_plural = "Stocks por punto"
        constraints = [
            models.UniqueConstraint(
                fields=["punto_inventario", "producto"],
                name="uq_stock_punto_producto",
            ),
            models.CheckConstraint(
                check=models.Q(cantidad__gte=0),
                name="chk_stock_punto_cantidad_no_negativa",
            ),
            models.CheckConstraint(
                check=models.Q(cantidad_minima__gte=0),
                name="chk_stock_punto_cantidad_minima_no_negativa",
            ),
        ]
        indexes = [
            models.Index(fields=["veterinaria", "producto"], name="idx_stock_tenant_prod"),
        ]

    def __str__(self):
        return f"{self.producto_id} @ {self.punto_inventario_id}: {self.cantidad}"
