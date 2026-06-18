from django.db import models


class TransaccionPago(models.Model):
    id_transaccion = models.AutoField(primary_key=True)
    pago = models.ForeignKey(
        "GestiondeVentasyPagos.Pago",
        db_column="id_pago",
        on_delete=models.CASCADE,
        related_name="transacciones",
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="transacciones_pago",
        null=True,
        blank=True,
    )
    provider = models.CharField(max_length=50)
    provider_reference = models.CharField(max_length=255, null=True, blank=True)
    estado = models.CharField(max_length=50)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=10, default="USD")
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "transaccion_pago"
        verbose_name = "Transacción de pago"
        verbose_name_plural = "Transacciones de pago"

    def __str__(self):
        return f"Transaccion #{self.id_transaccion} - Pago #{self.pago_id} ({self.estado})"
