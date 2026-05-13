# Generated migration for BackupConfig model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("AutenticacionySeguridad", "0008_enforce_not_null_veterinaria"),
    ]

    operations = [
        migrations.CreateModel(
            name="BackupConfig",
            fields=[
                ("id_backup_config", models.AutoField(primary_key=True, serialize=False)),
                ("frecuencia", models.CharField(
                    choices=[
                        ("DIARIO", "Diario"),
                        ("SEMANAL", "Semanal"),
                        ("MENSUAL", "Mensual"),
                        ("PERSONALIZADO", "Personalizado"),
                    ],
                    default="SEMANAL",
                    max_length=20,
                )),
                ("dias_retención", models.IntegerField(default=30)),
                ("último_backup", models.DateTimeField(blank=True, null=True)),
                ("próximo_backup_programado", models.DateTimeField(blank=True, null=True)),
                ("activo", models.BooleanField(default=True)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("actualizado", models.DateTimeField(auto_now=True)),
                (
                    "veterinaria",
                    models.OneToOneField(
                        db_column="id_veterinaria",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="backup_config",
                        to="AutenticacionySeguridad.veterinaria",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuración de backup",
                "verbose_name_plural": "Configuraciones de backup",
                "db_table": "backup_config",
            },
        ),
    ]
