from django.db import models


class GrupoUsuario(models.Model):
    id_grupo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    es_base = models.BooleanField(default=False)
    rol_base = models.CharField(max_length=50, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    veterinaria = models.ForeignKey(
        "AutenticacionySeguridad.Veterinaria",
        db_column="id_veterinaria",
        on_delete=models.CASCADE,
        related_name="grupos_usuario",
        null=False,
        blank=False,
    )

    class Meta:
        db_table = "grupo_usuario"
        verbose_name = "Grupo de usuario"
        verbose_name_plural = "Grupos de usuario"

    def __str__(self):
        return self.nombre
