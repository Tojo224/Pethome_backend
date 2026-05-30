from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestionInventarioProveedores", "0011_movimiento_lote_vencimiento"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="stockpunto",
            name="uq_stock_punto_producto",
        ),
        migrations.AddConstraint(
            model_name="stockpunto",
            constraint=models.UniqueConstraint(
                fields=("punto_inventario", "producto", "numero_lote"),
                name="uq_stock_punto_producto_lote",
            ),
        ),
    ]

