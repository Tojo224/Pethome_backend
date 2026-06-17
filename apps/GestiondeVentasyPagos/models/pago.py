from django.conf import settings
from django.db import models


class Pago(models.Model):
    class TipoReferencia(models.TextChoices):
        VENTA_WEB = "VENTA_WEB", "Venta registrada desde Web"
        PEDIDO_MOVIL = "PEDIDO_MOVIL", "Pedido de productos desde Móvil"
        CITA_SERVICIO = "CITA_SERVICIO", "Cita o servicio veterinario"
        SAAS_SUSCRIPCION = "SAAS_SUSCRIPCION", "Suscripción SaaS"

    class MetodoPago(models.TextChoices):
        STRIPE = "STRIPE", "Stripe"
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia bancaria"
        QR = "QR", "QR"
        ADMINISTRATIVO = "ADMINISTRATIVO", "Administrativo"

    class EstadoPago(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        PAGADO = "PAGADO", "Pagado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        FALLIDO = "FALLIDO", "Fallido"
        ANULADO = "ANULADO", "Anulado"

    id_pago = models.AutoField(primary_key=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="pagos",
        null=True,
        blank=True,
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_usuario",
        on_delete=models.PROTECT,
        related_name="pagos_registrados",
        null=True,
        blank=True,
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_cliente",
        on_delete=models.PROTECT,
        related_name="pagos_como_cliente",
        null=True,
        blank=True,
    )
    tipo_referencia = models.CharField(max_length=30, choices=TipoReferencia.choices)
    referencia_id = models.IntegerField()
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices)
    estado_pago = models.CharField(
        max_length=20,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE,
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=10, default="USD")
    stripe_session_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    codigo_transaccion = models.CharField(max_length=120, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pago"
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        indexes = [
            models.Index(fields=["veterinaria", "tipo_referencia", "referencia_id"]),
            models.Index(fields=["stripe_session_id"]),
        ]

    def __str__(self):
        return f"Pago #{self.id_pago} - {self.tipo_referencia} #{self.referencia_id} ({self.estado_pago})"
