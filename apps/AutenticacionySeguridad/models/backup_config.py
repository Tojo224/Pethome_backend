from django.db import models
from django.contrib.postgres.fields import ArrayField


class BackupConfig(models.Model):
    FRECUENCIAS = [
        ("DIARIO", "Diario"),
        ("SEMANAL", "Semanal"),
        ("MENSUAL", "Mensual"),
        ("PERSONALIZADO", "Personalizado"),
    ]

    id_backup_config = models.AutoField(primary_key=True)
    veterinaria = models.OneToOneField(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.CASCADE,
        related_name="backup_config",
        null=False,
        blank=False,
    )
    frecuencia = models.CharField(
        max_length=20, choices=FRECUENCIAS, default="SEMANAL"
    )
    dias_retención = models.IntegerField(default=30, db_column="dias_retenciÃ³n")
    último_backup = models.DateTimeField(null=True, blank=True, db_column="Ãºltimo_backup")
    próximo_backup_programado = models.DateTimeField(null=True, blank=True, db_column="prÃ³ximo_backup_programado")
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    # Campos para personalización (cuando frecuencia == "PERSONALIZADO")
    hora_ejecucion = models.IntegerField(default=2, help_text="Hora del día 0-23")
    minuto_ejecucion = models.IntegerField(default=15, help_text="Minuto del día 0-59")
    dias_semana = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True,
        help_text="Días de semana [0-6] donde 0=lunes, 6=domingo"
    )

    class Meta:
        db_table = "backup_config"
        verbose_name = "Configuración de backup"
        verbose_name_plural = "Configuraciones de backup"

    def __str__(self):
        return f"Backup Config - {self.veterinaria.nombre} ({self.frecuencia})"
