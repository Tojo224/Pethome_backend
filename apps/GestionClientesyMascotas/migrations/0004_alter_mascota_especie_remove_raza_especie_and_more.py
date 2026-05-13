import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestionServiciosyReserva", "0008_especie_raza"),
        ("GestionClientesyMascotas", "0003_enforce_not_null_veterinaria"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="mascota",
                    name="especie",
                    field=models.ForeignKey(
                        db_column="id_especie",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mascotas",
                        to="GestionServiciosyReserva.especie",
                    ),
                ),
                migrations.AlterField(
                    model_name="mascota",
                    name="raza",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="id_raza",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mascotas",
                        to="GestionServiciosyReserva.raza",
                    ),
                ),
                migrations.DeleteModel(name="Raza"),
                migrations.DeleteModel(name="Especie"),
            ],
        ),
    ]
