from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("AutenticacionySeguridad", "0021_alter_grupousuario_veterinaria"),
        ("GestionServiciosyReserva", "0008_especie_raza"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnidadMovilAsignacion",
            fields=[
                ("id_asignacion", models.AutoField(primary_key=True, serialize=False)),
                ("zona_nombre", models.CharField(max_length=120)),
                ("zona_descripcion", models.TextField(blank=True, null=True)),
                ("zona_geojson", models.JSONField(blank=True, null=True)),
                ("fecha_inicio", models.DateField()),
                ("fecha_fin", models.DateField(blank=True, null=True)),
                ("hora_inicio", models.TimeField(blank=True, null=True)),
                ("hora_fin", models.TimeField(blank=True, null=True)),
                ("estado", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "unidad",
                    models.ForeignKey(
                        db_column="id_unidad",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="asignaciones_logisticas",
                        to="GestionServiciosyReserva.unidadmovil",
                    ),
                ),
                (
                    "veterinaria",
                    models.ForeignKey(
                        db_column="id_veterinaria",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="asignaciones_logisticas",
                        to="AutenticacionySeguridad.veterinaria",
                    ),
                ),
            ],
            options={
                "verbose_name": "Asignacion de unidad movil",
                "verbose_name_plural": "Asignaciones de unidad movil",
                "db_table": "unidad_movil_asignacion",
                "ordering": ["-fecha_inicio", "id_asignacion"],
            },
        ),
        migrations.CreateModel(
            name="UnidadMovilAsignacionPersonal",
            fields=[
                ("id_asignacion_personal", models.AutoField(primary_key=True, serialize=False)),
                (
                    "rol_operativo",
                    models.CharField(
                        choices=[
                            ("VETERINARIO", "Veterinario"),
                            ("CHOFER", "Chofer"),
                            ("AUXILIAR", "Auxiliar"),
                            ("APOYO", "Apoyo"),
                        ],
                        default="VETERINARIO",
                        max_length=30,
                    ),
                ),
                ("es_responsable", models.BooleanField(default=False)),
                ("estado", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "asignacion",
                    models.ForeignKey(
                        db_column="id_asignacion",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="personal_asignado",
                        to="GestionServiciosyReserva.unidadmovilasignacion",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="asignaciones_unidad_movil",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Personal asignado a unidad movil",
                "verbose_name_plural": "Personal asignado a unidades moviles",
                "db_table": "unidad_movil_asignacion_personal",
                "ordering": ["id_asignacion_personal"],
            },
        ),
        migrations.AddConstraint(
            model_name="unidadmovilasignacionpersonal",
            constraint=models.UniqueConstraint(
                fields=("asignacion", "usuario"),
                name="uq_asignacion_personal_usuario",
            ),
        ),
    ]
