from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "AutenticacionySeguridad",
            "0017_merge_0014_user_bloqueado_hasta_user_intentos_fallidos_and_more_0016_backupconfig_minuto_ejecucion",
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="backupconfig",
                    name="dias_retención",
                    field=models.IntegerField(default=30, db_column="dias_retenciÃ³n"),
                ),
                migrations.AlterField(
                    model_name="backupconfig",
                    name="último_backup",
                    field=models.DateTimeField(
                        blank=True,
                        null=True,
                        db_column="Ãºltimo_backup",
                    ),
                ),
                migrations.AlterField(
                    model_name="backupconfig",
                    name="próximo_backup_programado",
                    field=models.DateTimeField(
                        blank=True,
                        null=True,
                        db_column="prÃ³ximo_backup_programado",
                    ),
                ),
            ],
        ),
    ]
