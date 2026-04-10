from django.conf import settings
from django.db import models

from .tipomascota import TipoMascota


class Mascota(models.Model):
    class SexoChoices(models.TextChoices):
        MACHO = "MACHO", "Macho"
        HEMBRA = "HEMBRA", "Hembra"

    id_mascota = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mascotas",
        db_column="id_usuario",
    )
    tipo_mascota = models.ForeignKey(
        TipoMascota,
        on_delete=models.PROTECT,
        related_name="mascotas",
        db_column="id_tipo_mascota",
    )
    nombre = models.CharField(max_length=100)
    color = models.CharField(max_length=100, blank=True, null=True)
    sexo = models.CharField(
        max_length=10,
        choices=SexoChoices.choices,
        blank=True,
        null=True,
    )
    fecha_nac = models.DateField(blank=True, null=True)
    tamano = models.CharField(max_length=50, blank=True, null=True)
    peso = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    foto = models.CharField(max_length=255, blank=True, null=True)
    alergias = models.TextField(blank=True, null=True)
    notas_generales = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "mascota"
        verbose_name = "Mascota"
        verbose_name_plural = "Mascotas"

    def __str__(self):
        return self.nombre
