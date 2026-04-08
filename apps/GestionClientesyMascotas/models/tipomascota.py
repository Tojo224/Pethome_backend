from django.db import models


class TipoMascota(models.Model):
    id_tipo_mascota = models.AutoField(primary_key=True)
    especie = models.CharField(max_length=100)
    raza = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "tipo_mascota"
        verbose_name = "Tipo de Mascota"
        verbose_name_plural = "Tipos de Mascota"

    def __str__(self):
        return f"{self.especie} - {self.raza}"
