# Generated manually for CU-20 rutas programadas.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("AutenticacionySeguridad", "0013_alter_rol_nombre"),
        ("GestionServiciosyReserva", "0006_reset_primary_key_sequences"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UnidadMovil",
            fields=[
                ("id_unidad", models.AutoField(primary_key=True, serialize=False)),
                ("nombre", models.CharField(max_length=100)),
                ("placa", models.CharField(blank=True, max_length=20, null=True)),
                ("descripcion", models.TextField(blank=True, null=True)),
                ("estado", models.BooleanField(default=True)),
                (
                    "veterinaria",
                    models.ForeignKey(
                        db_column="id_veterinaria",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="unidades_moviles",
                        to="AutenticacionySeguridad.veterinaria",
                    ),
                ),
            ],
            options={
                "db_table": "unidad_movil",
                "verbose_name": "Unidad movil",
                "verbose_name_plural": "Unidades moviles",
                "ordering": ["nombre", "id_unidad"],
            },
        ),
        migrations.CreateModel(
            name="RutaProgramada",
            fields=[
                ("id_ruta", models.AutoField(primary_key=True, serialize=False)),
                ("nombre", models.CharField(max_length=100)),
                ("fecha", models.DateField()),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PROGRAMADA", "Programada"),
                            ("EN_PROCESO", "En proceso"),
                            ("FINALIZADA", "Finalizada"),
                            ("CANCELADA", "Cancelada"),
                        ],
                        default="PROGRAMADA",
                        max_length=30,
                    ),
                ),
                (
                    "unidad",
                    models.ForeignKey(
                        db_column="id_unidad",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rutas_programadas",
                        to="GestionServiciosyReserva.unidadmovil",
                    ),
                ),
                (
                    "veterinaria",
                    models.ForeignKey(
                        db_column="id_veterinaria",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rutas_programadas",
                        to="AutenticacionySeguridad.veterinaria",
                    ),
                ),
                (
                    "veterinario",
                    models.ForeignKey(
                        db_column="id_veterinario",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rutas_programadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "ruta_programada",
                "verbose_name": "Ruta programada",
                "verbose_name_plural": "Rutas programadas",
                "ordering": ["fecha", "id_ruta"],
            },
        ),
        migrations.CreateModel(
            name="DetalleRuta",
            fields=[
                ("id_detalle_ruta", models.AutoField(primary_key=True, serialize=False)),
                ("orden", models.IntegerField()),
                ("hora_estimada", models.TimeField(blank=True, null=True)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente"),
                            ("EN_CAMINO", "En camino"),
                            ("ATENDIENDO", "Atendiendo"),
                            ("COMPLETADA", "Completada"),
                            ("CANCELADA", "Cancelada"),
                            ("INCIDENCIA", "Incidencia"),
                        ],
                        default="PENDIENTE",
                        max_length=30,
                    ),
                ),
                (
                    "cita",
                    models.ForeignKey(
                        db_column="id_cita",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="detalles_ruta",
                        to="GestionServiciosyReserva.cita",
                    ),
                ),
                (
                    "ruta",
                    models.ForeignKey(
                        db_column="id_ruta",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="detalles",
                        to="GestionServiciosyReserva.rutaprogramada",
                    ),
                ),
            ],
            options={
                "db_table": "detalle_ruta",
                "verbose_name": "Detalle de ruta",
                "verbose_name_plural": "Detalles de ruta",
                "ordering": ["orden", "id_detalle_ruta"],
            },
        ),
        migrations.AddConstraint(
            model_name="detalleruta",
            constraint=models.UniqueConstraint(
                fields=("ruta", "cita"),
                name="uq_detalle_ruta_cita_por_ruta",
            ),
        ),
        migrations.AddConstraint(
            model_name="detalleruta",
            constraint=models.UniqueConstraint(
                fields=("ruta", "orden"),
                name="uq_detalle_ruta_orden_por_ruta",
            ),
        ),
    ]
