from django.db import models


class ArchivoClinico(models.Model):
    class TipoArchivo(models.TextChoices):
        IMAGEN = "IMAGEN", "Imagen"
        PDF = "PDF", "PDF"
        WORD = "WORD", "Word"
        OTRO = "OTRO", "Otro"

    id_archivo_clinico = models.AutoField(primary_key=True)
    consulta_clinica = models.ForeignKey(
        "GestionarClinicaVeterinaria.ConsultaClinica",
        db_column="id_consulta_clinica",
        on_delete=models.CASCADE,
        related_name="archivos_clinicos",
    )
    nombre_archivo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to="historial_clinico/")
    tipo_archivo = models.CharField(
        max_length=20,
        choices=TipoArchivo.choices,
        default=TipoArchivo.OTRO,
    )
    extension = models.CharField(max_length=20, blank=True, null=True)
    tamano_bytes = models.BigIntegerField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = "archivo_clinico"
        verbose_name = "Archivo clínico"
        verbose_name_plural = "Archivos clínicos"

    def __str__(self):
        return self.nombre_archivo