from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("AutenticacionySeguridad", "0025_alter_backupconfig_dias_retención_and_more"),
        ("GestionServiciosyReserva", "0009_unidadmovilasignacion_and_more"),
        ("GestionClientesyMascotas", "0004_alter_mascota_especie_remove_raza_especie_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Adopcion",
            fields=[
                ("id_adopcion", models.AutoField(primary_key=True, serialize=False)),
                ("nombre", models.CharField(max_length=100)),
                ("foto", models.CharField(blank=True, max_length=255, null=True)),
                ("edad_aproximada", models.CharField(blank=True, max_length=80, null=True)),
                ("sexo", models.CharField(blank=True, choices=[("MACHO", "Macho"), ("HEMBRA", "Hembra")], max_length=10, null=True)),
                ("tamano", models.CharField(blank=True, choices=[("Pequeno", "Pequeno"), ("Mediano", "Mediano"), ("Grande", "Grande")], max_length=20, null=True)),
                ("ubicacion", models.CharField(max_length=180)),
                ("estado_adopcion", models.CharField(choices=[("disponible", "Disponible"), ("en_proceso", "En proceso"), ("adoptado", "Adoptado"), ("inactivo", "Inactivo")], default="disponible", max_length=20)),
                ("descripcion", models.TextField()),
                ("estado_salud", models.TextField()),
                ("fecha_publicacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                ("especie", models.ForeignKey(db_column="id_especie", on_delete=django.db.models.deletion.PROTECT, related_name="adopciones", to="GestionServiciosyReserva.especie")),
                ("raza", models.ForeignKey(blank=True, db_column="id_raza", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="adopciones", to="GestionServiciosyReserva.raza")),
                ("usuario", models.ForeignKey(db_column="id_usuario", on_delete=django.db.models.deletion.CASCADE, related_name="adopciones", to=settings.AUTH_USER_MODEL)),
                ("veterinaria", models.ForeignKey(db_column="id_veterinaria", on_delete=django.db.models.deletion.PROTECT, related_name="adopciones", to="AutenticacionySeguridad.veterinaria")),
            ],
            options={
                "verbose_name": "Adopcion",
                "verbose_name_plural": "Adopciones",
                "db_table": "adopcion",
                "ordering": ["-fecha_publicacion"],
            },
        ),
    ]
