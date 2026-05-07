from django.db import models
from .especie import Especie


class Raza(models.Model):
    id_raza = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    especie = models.ForeignKey(
        Especie,
        db_column="id_especie",
        on_delete=models.PROTECT,
        related_name="razas",
    )

    class Meta:
        db_table = "raza"
        verbose_name = "Raza"
        verbose_name_plural = "Razas"
        unique_together = ("especie", "nombre")

    def __str__(self):
        return f"{self.nombre} - {self.especie.nombre}"