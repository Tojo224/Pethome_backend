from django.db import models
from django.utils import timezone
from datetime import timedelta


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
    numero_lote = models.CharField(max_length=100, blank=True, null=True)
    fecha_vencimiento_lote = models.DateField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_punto"
        verbose_name = "Stock por punto"
        verbose_name_plural = "Stocks por punto"
        constraints = [
            models.UniqueConstraint(
                fields=["punto_inventario", "producto", "numero_lote"],
                name="uq_stock_punto_producto_lote",
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

    def es_stock_bajo(self):
        """Verifica si el stock esta por debajo del minimo"""
        return self.cantidad <= self.cantidad_minima

    def es_stock_agotado(self):
        """Verifica si el stock esta agotado (cantidad = 0)"""
        return self.cantidad == 0

    def esta_vencido(self):
        """Verifica si el lote esta vencido"""
        if not self.fecha_vencimiento_lote:
            return False
        return self.fecha_vencimiento_lote <= timezone.now().date()

    def proximo_a_vencer(self, dias=None):
        """Verifica si el lote esta proximo a vencer"""
        if not self.fecha_vencimiento_lote:
            return False

        dias_alerta = dias
        if dias_alerta is None:
            dias_alerta = getattr(self.producto, "dias_alerta_vencimiento", None) or 30

        fecha_alerta = timezone.now().date() + timedelta(days=dias_alerta)
        return (
            self.fecha_vencimiento_lote <= fecha_alerta
            and self.fecha_vencimiento_lote > timezone.now().date()
        )
