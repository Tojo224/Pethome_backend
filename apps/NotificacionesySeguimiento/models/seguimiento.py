from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Seguimiento(models.Model):
    TIPOS_SEGUIMIENTO = [
        ("CITA", "Cita"),
        ("SERVICIO", "Servicio"),
        ("PEDIDO", "Pedido"),
        ("RUTA", "Ruta"),
    ]

    id_seguimiento = models.BigAutoField(primary_key=True)

    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        on_delete=models.PROTECT,
        related_name="seguimientos",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seguimientos",
    )

    cita = models.ForeignKey(
        "GestionServiciosyReserva.Cita",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="seguimientos",
    )

    pedido = models.ForeignKey(
        "NotificacionesySeguimiento.Pedido",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="seguimientos",
    )

    tipo_seguimiento = models.CharField(max_length=30, choices=TIPOS_SEGUIMIENTO)
    estado_anterior = models.CharField(max_length=30, null=True, blank=True)
    estado_actual = models.CharField(max_length=30)

    descripcion = models.TextField(null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    visible_cliente = models.BooleanField(default=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "seguimiento"

    def clean(self):
        if self.cita and self.pedido:
            raise ValidationError(
                "Un seguimiento no puede pertenecer a una cita y a un pedido al mismo tiempo."
            )

        if not self.cita and not self.pedido:
            raise ValidationError(
                "El seguimiento debe estar asociado a una cita o a un pedido."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo_seguimiento} - {self.estado_actual}"
