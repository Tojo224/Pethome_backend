from django.conf import settings
from django.db import models

from apps.GestionServiciosyReserva.models.precioservicio import PrecioServicio
from apps.GestionServiciosyReserva.models.servicios import Servicio


class Cita(models.Model):
    class ModalidadChoices(models.TextChoices):
        CLINICA = "CLINICA", "Clinica"
        DOMICILIO = "DOMICILIO", "Domicilio"

    class EstadoChoices(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        CANCELADA = "CANCELADA", "Cancelada"
        COMPLETADA = "COMPLETADA", "Completada"

    id_cita = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="id_usuario",
        related_name="citas",
    )
    mascota = models.ForeignKey(
        "GestionClientesyMascotas.Mascota",
        on_delete=models.PROTECT,
        db_column="id_mascota",
        related_name="citas",
    )
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.PROTECT,
        db_column="id_servicio",
        related_name="citas",
    )
    precio_servicio = models.ForeignKey(
        PrecioServicio,
        on_delete=models.PROTECT,
        db_column="id_precio_servicio",
        related_name="citas",
    )

    fecha_generada = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(blank=True, null=True)
    fecha_programada = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField(blank=True, null=True)
    modalidad = models.CharField(max_length=20, choices=ModalidadChoices.choices)
    direccion_cita = models.TextField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PENDIENTE,
    )
    motivo_cancelacion = models.TextField(blank=True, null=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="citas",
        null=False,
        blank=False,
    )

    class Meta:
        db_table = "cita"
        verbose_name = "Cita"
        verbose_name_plural = "Citas"

    def __str__(self):
        return f"Cita #{self.id_cita} - {self.servicio.nombre}"
