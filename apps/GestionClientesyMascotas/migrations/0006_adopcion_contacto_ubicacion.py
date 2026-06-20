from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestionClientesyMascotas", "0005_adopcion"),
    ]

    operations = [
        migrations.AddField(
            model_name="adopcion",
            name="telefono_contacto",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="adopcion",
            name="referencia_ubicacion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="adopcion",
            name="latitud",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="adopcion",
            name="longitud",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
    ]
