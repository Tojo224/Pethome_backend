from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from apps.GestionServiciosyReserva.models.especie import Especie
from apps.GestionServiciosyReserva.models.raza import Raza


class Mascota(models.Model):
    SEXO_CHOICES = [
        ("MACHO", "Macho"),
        ("HEMBRA", "Hembra"),
    ]

    id_mascota = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_usuario",
        on_delete=models.CASCADE,
        related_name="mascotas",
    )
    especie = models.ForeignKey(
        Especie,
        db_column="id_especie",
        on_delete=models.PROTECT,
        related_name="mascotas",
    )
    raza = models.ForeignKey(
        Raza,
        db_column="id_raza",
        on_delete=models.PROTECT,
        related_name="mascotas",
        null=True,
        blank=True,
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="mascotas",
        null=False,
        blank=False,
    )

    nombre = models.CharField(max_length=100)
    color = models.CharField(max_length=100, null=True, blank=True)
    sexo = models.CharField(max_length=10, choices=SEXO_CHOICES, null=True, blank=True)
    fecha_nac = models.DateField(null=True, blank=True)
    tamano = models.CharField(max_length=50, null=True, blank=True)
    peso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    foto = models.CharField(max_length=255, null=True, blank=True)
    alergias = models.TextField(null=True, blank=True)
    notas_generales = models.TextField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "mascota"
        verbose_name = "Mascota"
        verbose_name_plural = "Mascotas"

    def clean(self):
        if self.raza and self.raza.especie_id != self.especie_id:
            raise ValidationError({
                "raza": "La raza seleccionada no pertenece a la especie indicada."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre
