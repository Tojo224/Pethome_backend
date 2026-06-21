from django.conf import settings
from django.db import models


class Pedido(models.Model):
    ESTADOS_PEDIDO = [
        ("PENDIENTE", "Pendiente"),
        ("CONFIRMADO", "Confirmado"),
        ("EN_PREPARACION", "En preparacion"),
        ("EN_CAMINO", "En camino"),
        ("ENTREGADO", "Entregado"),
        ("CANCELADO", "Cancelado"),
    ]

    TIPOS_ENTREGA = [
        ("DOMICILIO", "Domicilio"),
        ("RECOJO", "Recojo en veterinaria"),
    ]

    id_pedido = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos")
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    cita = models.ForeignKey(
        "GestionServiciosyReserva.Cita",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_producto",
    )

    fecha_pedido = models.DateTimeField(auto_now_add=True)
    direccion_entrega = models.TextField(null=True, blank=True)
    tipo_entrega = models.CharField(max_length=30, choices=TIPOS_ENTREGA, default="DOMICILIO")
    estado_pedido = models.CharField(max_length=30, choices=ESTADOS_PEDIDO, default="PENDIENTE")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    observacion = models.TextField(null=True, blank=True)
    motivo_cancelacion = models.TextField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "pedido"

    def __str__(self):
        return f"Pedido #{self.id_pedido} - {self.estado_pedido}"
