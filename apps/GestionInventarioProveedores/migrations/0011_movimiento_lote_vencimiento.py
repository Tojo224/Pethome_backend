from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestionInventarioProveedores", "0010_remove_producto_fecha_vencimiento"),
    ]

    operations = [
        migrations.AddField(
            model_name="movimientoinventario",
            name="fecha_vencimiento_lote",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="numero_lote",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]

