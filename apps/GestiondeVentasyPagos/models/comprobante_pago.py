from django.db import models


class ComprobantePago(models.Model):
    class TipoComprobante(models.TextChoices):
        FACTURA = "FACTURA", "Factura"
        RECIBO = "RECIBO", "Recibo"

    class EstadoComprobante(models.TextChoices):
        EMITIDO = "EMITIDO", "Emitido"
        ANULADO = "ANULADO", "Anulado"

    id_comprobante = models.AutoField(primary_key=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="comprobantes",
        null=True,
        blank=True,
    )
    pago = models.OneToOneField(
        "GestiondeVentasyPagos.Pago",
        db_column="id_pago",
        on_delete=models.PROTECT,
        related_name="comprobante",
    )
    numero_comprobante = models.CharField(max_length=50)
    tipo_comprobante = models.CharField(
        max_length=20,
        choices=TipoComprobante.choices,
        default=TipoComprobante.RECIBO,
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=50)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    detalle_items = models.JSONField(default=dict, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoComprobante.choices,
        default=EstadoComprobante.EMITIDO,
    )
    url_archivo = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "comprobante_pago"
        verbose_name = "Comprobante de pago"
        verbose_name_plural = "Comprobantes de pago"
        indexes = [
            models.Index(fields=["veterinaria", "numero_comprobante"]),
        ]

    def __str__(self):
        return f"{self.tipo_comprobante} {self.numero_comprobante} - Pago #{self.pago_id}"
