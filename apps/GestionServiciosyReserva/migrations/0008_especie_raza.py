import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestionClientesyMascotas", "0003_enforce_not_null_veterinaria"),
        ("GestionServiciosyReserva", "0007_unidadmovil_rutaprogramada_detalleruta"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Especie",
                    fields=[
                        ("id_especie", models.AutoField(primary_key=True, serialize=False)),
                        ("nombre", models.CharField(max_length=100, unique=True)),
                    ],
                    options={
                        "db_table": "especie",
                        "verbose_name": "Especie",
                        "verbose_name_plural": "Especies",
                    },
                ),
                migrations.CreateModel(
                    name="Raza",
                    fields=[
                        ("id_raza", models.AutoField(primary_key=True, serialize=False)),
                        ("nombre", models.CharField(max_length=100)),
                        (
                            "especie",
                            models.ForeignKey(
                                db_column="id_especie",
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="razas",
                                to="GestionServiciosyReserva.especie",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "raza",
                        "verbose_name": "Raza",
                        "verbose_name_plural": "Razas",
                        "unique_together": {("especie", "nombre")},
                    },
                ),
            ],
        ),
    ]
