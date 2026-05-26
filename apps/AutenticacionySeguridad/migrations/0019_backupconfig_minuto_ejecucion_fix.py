# Corrective migration for databases restored before minuto_ejecucion existed.
#
# This migration must be idempotent because some histories already added the
# column in migration 0016.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("AutenticacionySeguridad", "0018_alter_backupconfig_dias_retención_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE backup_config "
                        "ADD COLUMN IF NOT EXISTS minuto_ejecucion integer DEFAULT 15;"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="backupconfig",
                    name="minuto_ejecucion",
                    field=models.IntegerField(default=15, help_text="Minuto del día 0-59"),
                ),
            ],
        ),
    ]
