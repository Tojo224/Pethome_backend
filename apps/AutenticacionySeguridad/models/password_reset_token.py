from django.conf import settings
from django.db import models


class PasswordResetToken(models.Model):
    id_password_reset_token = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=255, unique=True)
    expiracion = models.DateTimeField()
    usado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_reset_tokens"
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"PasswordResetToken(usuario={self.usuario_id}, usado={self.usado})"
