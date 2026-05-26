from django.db import models


class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    contacto = models.CharField(max_length=150, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    ubicacion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.PROTECT,
        related_name="proveedores",
        null=False,
        blank=False,
    )

    class Meta:
        db_table = "proveedor"
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        constraints = [
            models.UniqueConstraint(
                fields=["veterinaria", "nombre"],
                name="uq_proveedor_veterinaria_nombre",
            )
        ]

    def __str__(self):
        return self.nombre
