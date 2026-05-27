from django.conf import settings
from django.db import models


class Venta(models.Model):
    class EstadoVenta(models.TextChoices):
        PENDIENTE_COBRO = "PENDIENTE_COBRO", "Pendiente de cobro"
        ANULADA = "ANULADA", "Anulada"

    id_venta = models.AutoField(primary_key=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="ventas",
    )
    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_usuario_responsable",
        on_delete=models.PROTECT,
        related_name="ventas_registradas",
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_cliente",
        on_delete=models.PROTECT,
        related_name="ventas_como_cliente",
        blank=True,
        null=True,
    )
    mascota = models.ForeignKey(
        "GestionClientesyMascotas.Mascota",
        db_column="id_mascota",
        on_delete=models.PROTECT,
        related_name="ventas",
        blank=True,
        null=True,
    )
    fecha_venta = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado_venta = models.CharField(
        max_length=20,
        choices=EstadoVenta.choices,
        default=EstadoVenta.PENDIENTE_COBRO,
    )
    observacion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "venta"
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        indexes = [
            models.Index(fields=["veterinaria", "fecha_venta"], name="idx_venta_tenant_fecha"),
            models.Index(fields=["veterinaria", "estado_venta"], name="idx_venta_tenant_estado"),
        ]

    def __str__(self):
        return f"Venta {self.id_venta} - {self.estado_venta}"

