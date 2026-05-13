# Generated migration to add custom schedule fields to BackupConfig

from django.db import migrations, models
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('AutenticacionySeguridad', '0014_merge_0009_backupconfig_0013_alter_rol_nombre'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupconfig',
            name='hora_ejecucion',
            field=models.IntegerField(default=2, help_text='Hora del día 0-23'),
        ),
        migrations.AddField(
            model_name='backupconfig',
            name='dias_semana',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.IntegerField(),
                blank=True,
                default=list,
                help_text='Días de semana [0-6] donde 0=lunes, 6=domingo',
                size=None
            ),
        ),
    ]
