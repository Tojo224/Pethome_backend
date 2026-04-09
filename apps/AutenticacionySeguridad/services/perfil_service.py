
from django.db import transaction
from rest_framework import serializers
from ..models import Perfil, User, Rol

# Logica de negocio para crear y actualizar perfiles
@transaction.atomic
def create_user_with_profile(*, correo, password, id_rol, nombre, telefono, direccion):
    try:
        rol = Rol.objects.get(pk=id_rol)
    except Rol.DoesNotExist as exc:
        raise serializers.ValidationError({"id_rol": "Rol inválido."}) from exc

    if User.objects.filter(correo=correo).exists():
        raise serializers.ValidationError({"correo": "El correo ya está registrado."})

    user = User.objects.create_user(
        correo=correo,
        password=password,
        role=rol,
    )

    perfil = Perfil.objects.create(
        usuario=user,
        nombre=nombre,
        telefono=telefono,
        direccion=direccion,
    )

    return perfil


@transaction.atomic
def update_user_with_profile(
    *,
    perfil,
    correo=None,
    password=None,
    id_rol=None,
    estado=None,
    nombre=None,
    telefono=None,
    direccion=None,
):
    user = perfil.usuario

    if correo and User.objects.exclude(pk=user.pk).filter(correo=correo).exists():
        raise serializers.ValidationError({"correo": "El correo ya está registrado."})

    if correo:
        user.correo = correo

    if password:
        user.set_password(password)

    if id_rol is not None:
        try:
            user.role = Rol.objects.get(pk=id_rol)
        except Rol.DoesNotExist as exc:
            raise serializers.ValidationError({"id_rol": "Rol inválido."}) from exc

    if estado is not None:
        user.is_active = estado

    user.save()

    if nombre is not None:
        perfil.nombre = nombre

    if telefono is not None:
        perfil.telefono = telefono

    if direccion is not None:
        perfil.direccion = direccion

    perfil.save()
    return perfil


@transaction.atomic
def deactivate_user_profile(*, perfil):
    perfil.usuario.is_active = False
    perfil.usuario.save(update_fields=["is_active"])
    return perfil

@transaction.atomic
def activate_user_profile(*, perfil):
    perfil.usuario.is_active = True
    perfil.usuario.save(update_fields=["is_active"])
    return perfil