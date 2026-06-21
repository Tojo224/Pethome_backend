from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("NotificacionesySeguimiento", "0006_pedido_cita"),
        ("GestionServiciosyReserva", "0009_unidadmovilasignacion_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="detalleruta",
            name="cita",
            field=models.ForeignKey(
                blank=True,
                db_column="id_cita",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="detalles_ruta",
                to="GestionServiciosyReserva.cita",
            ),
        ),
        migrations.AddField(
            model_name="detalleruta",
            name="pedido",
            field=models.ForeignKey(
                blank=True,
                db_column="id_pedido",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="detalles_ruta",
                to="NotificacionesySeguimiento.pedido",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="detalleruta",
            name="uq_detalle_ruta_cita_por_ruta",
        ),
        migrations.AddConstraint(
            model_name="detalleruta",
            constraint=models.UniqueConstraint(
                condition=Q(cita__isnull=False),
                fields=("ruta", "cita"),
                name="uq_detalle_ruta_cita_por_ruta",
            ),
        ),
        migrations.AddConstraint(
            model_name="detalleruta",
            constraint=models.UniqueConstraint(
                condition=Q(pedido__isnull=False),
                fields=("ruta", "pedido"),
                name="uq_detalle_ruta_pedido_por_ruta",
            ),
        ),
        migrations.AddConstraint(
            model_name="detalleruta",
            constraint=models.CheckConstraint(
                check=Q(cita__isnull=False) | Q(pedido__isnull=False),
                name="ck_detalle_ruta_referencia_requerida",
            ),
        ),
    ]
