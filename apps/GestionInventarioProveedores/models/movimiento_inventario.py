from django.conf import settings
from django.db import models


class MovimientoInventario(models.Model):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"
        CONSUMO = "CONSUMO", "Consumo"
        REPOSICION = "REPOSICION", "Reposicion"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        DEVOLUCION = "DEVOLUCION", "Devolucion"
        AJUSTE = "AJUSTE", "Ajuste"

    id_movimiento = models.AutoField(primary_key=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
    )
    producto = models.ForeignKey(
        "GestionInventarioProveedores.Producto",
        db_column="id_producto",
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_usuario",
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
    )
    punto_origen = models.ForeignKey(
        "GestionInventarioProveedores.PuntoInventario",
        db_column="id_punto_origen",
        on_delete=models.PROTECT,
        related_name="movimientos_salida",
        blank=True,
        null=True,
    )
    punto_destino = models.ForeignKey(
        "GestionInventarioProveedores.PuntoInventario",
        db_column="id_punto_destino",
        on_delete=models.PROTECT,
        related_name="movimientos_entrada",
        blank=True,
        null=True,
    )
    tipo = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    numero_lote = models.CharField(max_length=100, blank=True, null=True)
    fecha_vencimiento_lote = models.DateField(blank=True, null=True)
    cantidad_anterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cantidad_posterior = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    motivo = models.TextField(blank=True, null=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "movimiento_inventario"
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        indexes = [
            models.Index(fields=["veterinaria", "fecha_movimiento"], name="idx_mov_tenant_fecha"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name="chk_movimiento_cantidad_mayor_cero",
            ),
        ]

    def __str__(self):
        return f"{self.tipo} {self.producto_id} x {self.cantidad}"
