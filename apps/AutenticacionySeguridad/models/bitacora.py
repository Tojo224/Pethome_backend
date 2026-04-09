from django.conf import settings
from django.db import models

from ..events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)


class Bitacora(models.Model):

    id_bitacora = models.AutoField(primary_key=True)

    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        db_column="fecha_hora",
        help_text="Fecha y hora en que ocurrió el evento."
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column="id_usuario",
        related_name="bitacora_eventos",
        null=True,
        blank=True,
        help_text="Usuario que ejecutó la acción. Puede ser nulo para eventos del sistema o anónimos."
    )

    accion = models.CharField(
        max_length=50,
        choices=BitacoraAccion.choices,
        help_text="Acción realizada en el sistema."
    )

    descripcion = models.TextField(
        blank=True,
        default="",
        help_text="Descripción legible del evento."
    )

    ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Dirección IP desde donde se originó la acción."
    )

    user_agent = models.TextField(
        blank=True,
        default="",
        help_text="Información del navegador o cliente."
    )

    modulo = models.CharField(
        max_length=100,
        choices=BitacoraModulo.choices,
        blank=True,
        default=BitacoraModulo.SISTEMA,
        help_text="Módulo del sistema donde ocurrió el evento."
    )

    entidad_tipo = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Tipo de entidad afectada. Ejemplo: Usuario, Herramienta, Prestamo."
    )

    entidad_id = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Identificador de la entidad afectada."
    )

    resultado = models.CharField(
        max_length=10,
        choices=BitacoraResultado.choices,
        default=BitacoraResultado.EXITO,
        help_text="Resultado del evento."
    )

    metadatos = models.JSONField(
        blank=True,
        default=dict,
        help_text="Información adicional del evento en formato JSON."
    )

    class Meta:
        db_table = "bitacora"
        verbose_name = "Bitácora"
        verbose_name_plural = "Bitácora"
        ordering = ["-fecha_hora"]
        indexes = [
            models.Index(fields=["fecha_hora"]),
            models.Index(fields=["accion"]),
            models.Index(fields=["resultado"]),
            models.Index(fields=["modulo"]),
            models.Index(fields=["usuario", "fecha_hora"]),
            models.Index(fields=["entidad_tipo", "entidad_id"]),
        ]

    def __str__(self):
        usuario = getattr(self.usuario, "username", None) or "Sistema/Anónimo"
        return f"{self.fecha_hora} - {usuario} - {self.accion}"