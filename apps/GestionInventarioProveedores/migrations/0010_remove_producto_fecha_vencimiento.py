from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("GestionInventarioProveedores", "0009_agregar_control_vencimiento"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="producto",
            name="fecha_vencimiento",
        ),
    ]

