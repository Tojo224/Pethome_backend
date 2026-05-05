from django.db import models

from .encrypted_fields import EncryptedJSONField


class Bitacora(models.Model):
    id_bitacora = models.AutoField(primary_key=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        on_delete=models.PROTECT,
        db_column="id_veterinaria",
        related_name="bitacoras",
        null=True,
        blank=True,
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")
    payload = EncryptedJSONField()

    class Meta:
        db_table = "bitacora"
        verbose_name = "Bitacora"
        verbose_name_plural = "Bitacora"
        ordering = ["-fecha_hora"]
        indexes = [
            models.Index(fields=["veterinaria", "-fecha_hora"], name="idx_bitacora_vet_fecha"),
        ]

    def __str__(self):
        return f"Bitacora #{self.id_bitacora} - {self.fecha_hora}"
