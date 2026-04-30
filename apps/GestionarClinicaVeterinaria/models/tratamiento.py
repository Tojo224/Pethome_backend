from django.db import models


class Tratamiento(models.Model):
    class TipoTratamiento(models.TextChoices):
        MEDICAMENTO = "MEDICAMENTO", "Medicamento"
        PROCEDIMIENTO = "PROCEDIMIENTO", "Procedimiento"
        TERAPIA = "TERAPIA", "Terapia"
        OTRO = "OTRO", "Otro"

    class EstadoTratamiento(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_CURSO = "EN_CURSO", "En curso"
        FINALIZADO = "FINALIZADO", "Finalizado"
        CANCELADO = "CANCELADO", "Cancelado"

    id_tratamiento = models.AutoField(primary_key=True)
    consulta_clinica = models.ForeignKey(
        "GestionarClinicaVeterinaria.ConsultaClinica",
        db_column="id_consulta_clinica",
        on_delete=models.CASCADE,
        related_name="tratamientos",
    )
    tipo = models.CharField(
        max_length=30,
        choices=TipoTratamiento.choices,
        default=TipoTratamiento.OTRO,
    )
    descripcion = models.TextField()
    fecha_ini = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)
    estado_tratamiento = models.CharField(
        max_length=20,
        choices=EstadoTratamiento.choices,
        default=EstadoTratamiento.PENDIENTE,
    )
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tratamiento"
        verbose_name = "Tratamiento"
        verbose_name_plural = "Tratamientos"

    def __str__(self):
        return f"Tratamiento #{self.id_tratamiento}"