# Generated manually to add RUTA as seguimiento type.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("NotificacionesySeguimiento", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="seguimiento",
            name="tipo_seguimiento",
            field=models.CharField(
                choices=[
                    ("CITA", "Cita"),
                    ("SERVICIO", "Servicio"),
                    ("PEDIDO", "Pedido"),
                    ("RUTA", "Ruta"),
                ],
                max_length=30,
            ),
        ),
    ]
