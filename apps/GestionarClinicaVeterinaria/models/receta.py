from django.db import models


class Receta(models.Model):
    id_receta = models.AutoField(primary_key=True)
    consulta_clinica = models.OneToOneField(
        "GestionarClinicaVeterinaria.ConsultaClinica",
        db_column="id_consulta_clinica",
        on_delete=models.CASCADE,
        related_name="receta",
    )
    fecha = models.DateTimeField()
    indicaciones = models.TextField(blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "receta"
        verbose_name = "Receta"
        verbose_name_plural = "Recetas"

    def __str__(self):
        return f"Receta #{self.id_receta}"