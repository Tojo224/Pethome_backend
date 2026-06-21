from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("GestionServiciosyReserva", "0004_categoriaservicio_veterinaria_cita_veterinaria_and_more"),
        ("NotificacionesySeguimiento", "0005_alter_dispositivousuario_veterinaria"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="cita",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="pedidos_producto",
                to="GestionServiciosyReserva.cita",
            ),
        ),
    ]
