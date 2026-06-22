from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("AutenticacionySeguridad", "0025_alter_backupconfig_dias_retención_and_more"),
        ("GestionClientesyMascotas", "0006_adopcion_contacto_ubicacion"),
        ("GestionarClinicaVeterinaria", "0003_enforce_not_null_veterinaria"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlanSanitarioPreventivo",
            fields=[
                ("id_plan_sanitario", models.AutoField(primary_key=True, serialize=False)),
                (
                    "tipo_evento",
                    models.CharField(
                        choices=[
                            ("CONTROL", "Control"),
                            ("VACUNA", "Vacuna"),
                            ("DESPARASITACION", "Desparasitación"),
                            ("REVISION", "Revisión"),
                            ("OTRO", "Otro"),
                        ],
                        max_length=20,
                    ),
                ),
                ("descripcion", models.CharField(max_length=255)),
                ("fecha_programada", models.DateField()),
                (
                    "estado_plan",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente"),
                            ("REALIZADO", "Realizado"),
                            ("VENCIDO", "Vencido"),
                            ("CANCELADO", "Cancelado"),
                        ],
                        default="PENDIENTE",
                        max_length=15,
                    ),
                ),
                ("observaciones", models.TextField(blank=True, null=True)),
                ("estado", models.BooleanField(default=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                (
                    "mascota",
                    models.ForeignKey(
                        db_column="id_mascota",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="planes_sanitarios_preventivos",
                        to="GestionClientesyMascotas.mascota",
                    ),
                ),
                (
                    "usuario_registro",
                    models.ForeignKey(
                        db_column="id_usuario_registro",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="planes_sanitarios_registrados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "veterinaria",
                    models.ForeignKey(
                        db_column="id_veterinaria",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="planes_sanitarios_preventivos",
                        to="AutenticacionySeguridad.veterinaria",
                    ),
                ),
            ],
            options={
                "verbose_name": "Plan sanitario preventivo",
                "verbose_name_plural": "Planes sanitarios preventivos",
                "db_table": "plan_sanitario_preventivo",
                "ordering": ["fecha_programada", "-fecha_creacion"],
            },
        ),
    ]
