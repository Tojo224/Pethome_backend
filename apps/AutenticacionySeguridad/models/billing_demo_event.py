from django.db import models


class BillingDemoEvent(models.Model):
    class EventType(models.TextChoices):
        DIRECT_PURCHASE = "DIRECT_PURCHASE", "Compra directa"
        TRIAL_UPGRADE = "TRIAL_UPGRADE", "Upgrade desde prueba"

    class EventStatus(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        STARTED = "STARTED", "Iniciado"  # Compatibilidad legacy
        PAID = "PAID", "Pagado"
        CONFIRMED = "CONFIRMED", "Confirmado"
        FAILED = "FAILED", "Fallido"
        EXPIRED = "EXPIRED", "Expirado"
        CANCELLED = "CANCELLED", "Cancelado"

    id_billing_demo_event = models.AutoField(primary_key=True)
    checkout_token = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.STARTED,
    )
    plan = models.ForeignKey(
        "AutenticacionySeguridad.PlanSuscripcion",
        db_column="id_plan",
        on_delete=models.PROTECT,
        related_name="billing_demo_events",
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.CASCADE,
        related_name="billing_demo_events",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        "AutenticacionySeguridad.User",
        db_column="id_usuario",
        on_delete=models.SET_NULL,
        related_name="billing_demo_events",
        null=True,
        blank=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    payment_mode = models.CharField(max_length=20, default="DEMO")
    stripe_session_id = models.CharField(max_length=120, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=120, null=True, blank=True)
    stripe_event_id = models.CharField(max_length=120, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    expires_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_demo_event"
        verbose_name = "Evento de facturacion demo"
        verbose_name_plural = "Eventos de facturacion demo"
        indexes = [
            models.Index(fields=["status", "event_type"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.id_billing_demo_event} - {self.event_type} - {self.status}"
