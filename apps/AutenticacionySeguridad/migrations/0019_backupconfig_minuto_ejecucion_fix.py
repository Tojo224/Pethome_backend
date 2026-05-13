# Corrective migration for databases restored before minuto_ejecucion existed.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("AutenticacionySeguridad", "0018_alter_backupconfig_dias_retención_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="backupconfig",
            name="minuto_ejecucion",
            field=models.IntegerField(default=15, help_text="Minuto del dÃ­a 0-59"),
        ),
    ]
