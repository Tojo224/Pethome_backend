from django.db import models


class Veterinaria(models.Model):
    id_veterinaria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    nit = models.CharField(max_length=50, blank=True, null=True)
    correo = models.EmailField(max_length=150, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    logo = models.CharField(max_length=255, blank=True, null=True)
    estado = models.BooleanField(default=True)
    permite_auto_registro_clientes = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    owner_user = models.ForeignKey(
        "AutenticacionySeguridad.User",
        db_column="owner_user_id",
        on_delete=models.SET_NULL,
        related_name="veterinarias_propietarias",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "veterinaria"
        verbose_name = "Veterinaria"
        verbose_name_plural = "Veterinarias"

    def __str__(self):
        return self.nombre
