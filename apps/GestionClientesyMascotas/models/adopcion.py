from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.GestionServiciosyReserva.models.especie import Especie
from apps.GestionServiciosyReserva.models.raza import Raza


class Adopcion(models.Model):
    ESTADO_DISPONIBLE = "disponible"
    ESTADO_EN_PROCESO = "en_proceso"
    ESTADO_ADOPTADO = "adoptado"
    ESTADO_INACTIVO = "inactivo"

    ESTADO_CHOICES = [
        (ESTADO_DISPONIBLE, "Disponible"),
        (ESTADO_EN_PROCESO, "En proceso"),
        (ESTADO_ADOPTADO, "Adoptado"),
        (ESTADO_INACTIVO, "Inactivo"),
    ]

    SEXO_CHOICES = [
        ("MACHO", "Macho"),
        ("HEMBRA", "Hembra"),
    ]

    TAMANO_CHOICES = [
        ("Pequeno", "Pequeno"),
        ("Mediano", "Mediano"),
        ("Grande", "Grande"),
    ]

    id_adopcion = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_usuario",
        on_delete=models.CASCADE,
        related_name="adopciones",
    )
    especie = models.ForeignKey(
        Especie,
        db_column="id_especie",
        on_delete=models.PROTECT,
        related_name="adopciones",
    )
    raza = models.ForeignKey(
        Raza,
        db_column="id_raza",
        on_delete=models.PROTECT,
        related_name="adopciones",
        null=True,
        blank=True,
    )
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="adopciones",
    )

    nombre = models.CharField(max_length=100)
    foto = models.CharField(max_length=255, null=True, blank=True)
    edad_aproximada = models.CharField(max_length=80, null=True, blank=True)
    sexo = models.CharField(max_length=10, choices=SEXO_CHOICES, null=True, blank=True)
    tamano = models.CharField(max_length=20, choices=TAMANO_CHOICES, null=True, blank=True)
    ubicacion = models.CharField(max_length=180)
    telefono_contacto = models.CharField(max_length=20, blank=True, default="")
    referencia_ubicacion = models.TextField(blank=True, default="")
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado_adopcion = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_DISPONIBLE,
    )
    descripcion = models.TextField()
    estado_salud = models.TextField()
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "adopcion"
        verbose_name = "Adopcion"
        verbose_name_plural = "Adopciones"
        ordering = ["-fecha_publicacion"]

    def clean(self):
        if self.raza and self.raza.especie_id != self.especie_id:
            raise ValidationError({
                "raza": "La raza seleccionada no pertenece a la especie indicada."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.estado_adopcion})"
