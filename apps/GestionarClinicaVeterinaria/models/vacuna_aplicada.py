from django.db import models


class VacunaAplicada(models.Model):
    class EstadoVacuna(models.TextChoices):
        APLICADA = "APLICADA", "Aplicada"
        PENDIENTE = "PENDIENTE", "Pendiente"
        REFUERZO = "REFUERZO", "Refuerzo"

    id_vacuna_aplicada = models.AutoField(primary_key=True)
    consulta_clinica = models.ForeignKey(
        "GestionarClinicaVeterinaria.ConsultaClinica",
        db_column="id_consulta_clinica",
        on_delete=models.CASCADE,
        related_name="vacunas_aplicadas",
    )
    nombre_vacuna = models.CharField(max_length=100)
    dosis = models.CharField(max_length=50, blank=True, null=True)
    fecha_aplicada = models.DateField()
    fecha_proxima = models.DateField(blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)
    lote = models.CharField(max_length=100, blank=True, null=True)
    fabricante = models.CharField(max_length=100, blank=True, null=True)
    estado_vacuna = models.CharField(
        max_length=20,
        choices=EstadoVacuna.choices,
        default=EstadoVacuna.APLICADA,
    )
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vacuna_aplicada"
        verbose_name = "Vacuna aplicada"
        verbose_name_plural = "Vacunas aplicadas"

    def __str__(self):
        return f"{self.nombre_vacuna} - {self.fecha_aplicada}"