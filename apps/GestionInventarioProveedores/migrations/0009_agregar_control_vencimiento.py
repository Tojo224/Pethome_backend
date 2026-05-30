# Generated on 2026-05-27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestionInventarioProveedores", "0008_producto_proveedor_uniques_y_validaciones"),
    ]

    operations = [
        # Agregar campos de vencimiento a Producto
        migrations.AddField(
            model_name="producto",
            name="requiere_control_vencimiento",
            field=models.BooleanField(
                default=False,
                help_text="Indica si el producto requiere control de fecha de vencimiento",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="fecha_vencimiento",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="producto",
            name="dias_alerta_vencimiento",
            field=models.IntegerField(
                default=30,
                help_text="Días de anticipación para alertar sobre vencimiento próximo",
            ),
        ),
        # Agregar campos de lote y vencimiento a StockPunto
        migrations.AddField(
            model_name="stockpunto",
            name="numero_lote",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="stockpunto",
            name="fecha_vencimiento_lote",
            field=models.DateField(blank=True, null=True),
        ),
    ]
