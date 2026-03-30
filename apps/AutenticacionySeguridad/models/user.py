from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from .managers import UserManager
from .rol import Rol


class User(AbstractBaseUser, PermissionsMixin):
    id_usuario = models.AutoField(primary_key=True)
    correo = models.EmailField(max_length=100, unique=True)
    role = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        db_column="id_rol",
        related_name="usuarios",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    # last_login es gestionado automáticamente por AbstractBaseUser

    objects = UserManager()

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "usuarios"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.correo