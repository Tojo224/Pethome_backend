from django.db import models
from django.conf import settings
from apps.AutenticacionySeguridad.models.veterinaria import Veterinaria

class DispositivoUsuario(models.Model):
    class PlataformaChoices(models.TextChoices):
        WEB = "WEB", "Navegador Web"
        ANDROID = "ANDROID", "Android"
        IOS = "IOS", "iOS"

    id_dispositivo = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="id_usuario",
        related_name="dispositivos"
    )
    veterinaria = models.ForeignKey(
        Veterinaria,
        on_delete=models.CASCADE,
        db_column="id_veterinaria",
        related_name="dispositivos"
    )
    token_fcm = models.TextField(unique=True)
    plataforma = models.CharField(
        max_length=10,
        choices=PlataformaChoices.choices
    )
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_conexion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dispositivo_usuario"
        verbose_name = "Dispositivo de Usuario"
        verbose_name_plural = "Dispositivos de Usuario"

    def __str__(self):
        return f"{self.usuario.correo} - {self.plataforma}"
