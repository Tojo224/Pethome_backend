from django.conf import settings
from django.db import models


class CarritoTemporal(models.Model):
    class EstadoCarrito(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        VACIADO = "VACIADO", "Vaciado"

    id_carrito = models.AutoField(primary_key=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="carritos_temporales",
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_cliente",
        on_delete=models.PROTECT,
        related_name="carritos_temporales",
    )
    estado_carrito = models.CharField(
        max_length=10,
        choices=EstadoCarrito.choices,
        default=EstadoCarrito.ACTIVO,
    )
    subtotal_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carrito_temporal"
        verbose_name = "Carrito temporal"
        verbose_name_plural = "Carritos temporales"
        indexes = [
            models.Index(fields=["veterinaria", "cliente", "estado_carrito"], name="idx_cart_tenant_cli_est"),
            models.Index(fields=["veterinaria", "fecha_creacion"], name="idx_cart_tenant_fecha"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["veterinaria", "cliente"],
                condition=models.Q(estado_carrito="ACTIVO", estado=True),
                name="uq_cart_active_tenant_client",
            ),
            models.CheckConstraint(
                check=models.Q(subtotal_estimado__gte=0),
                name="chk_cart_subtotal_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(total_estimado__gte=0),
                name="chk_cart_total_non_negative",
            ),
        ]

    def __str__(self):
        return f"Carrito {self.id_carrito} - Cliente {self.cliente_id}"
