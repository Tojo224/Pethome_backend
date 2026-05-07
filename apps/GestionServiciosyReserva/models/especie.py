from django.db import models


class Especie(models.Model):
    id_especie = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "especie"
        verbose_name = "Especie"
        verbose_name_plural = "Especies"

    def __str__(self):
        return self.nombre