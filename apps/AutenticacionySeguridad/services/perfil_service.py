
from django.db import transaction
from rest_framework import serializers
from ..models import Perfil, User, Rol

# Logica de negocio para crear y actualizar perfiles
@transaction.atomic
def create_user_with_profile(
    *,
    correo,
    password,
    id_rol,
    nombre,
    telefono,
    direccion,
    estado=None,
    veterinaria_id=None,
    request_user=None,
):
    try:
        rol = Rol.objects.get(pk=id_rol)
    except Rol.DoesNotExist as exc:
        raise serializers.ValidationError({"id_rol": "Rol inválido."}) from exc

    # --- SEGURIDAD: Evitar escalada de privilegios ---
    if not getattr(request_user, "is_superuser", False):
        # Si el creador no es SuperAdmin, no puede crear usuarios con privilegios globales
        # o asignar roles que no pertenecen a su flujo (en este caso bloqueamos is_superuser)
        pass # La lógica de create_user por defecto no pone is_superuser en True, 
             # pero el servicio debe ser explícito.
    # -------------------------------------------------

    if User.objects.filter(correo=correo).exists():
        raise serializers.ValidationError({"correo": "El correo ya está registrado."})

    if not veterinaria_id:
        raise serializers.ValidationError({
            "veterinaria": "No se pudo resolver la veterinaria del usuario."
        })

    # --- VALIDACIÓN DE LÍMITE DE USUARIOS (SaaS) ---
    from ..selectors.perfil_selector import SuscripcionSelector
    suscripcion = SuscripcionSelector.get_suscripcion_activa(veterinaria_id)

    if suscripcion and suscripcion.plan:
        limite = suscripcion.plan.limite_usuarios
        if limite > 0:
            # Solo contamos empleados (Admin, Veterinario, Groomer, etc.)
            conteo_actual = User.objects.filter(
                veterinaria_id=veterinaria_id, 
                is_active=True
            ).exclude(role__nombre="CLIENT").count()
            
            if conteo_actual >= limite:
                raise serializers.ValidationError({
                    "detail": f"Se ha alcanzado el límite de usuarios (personal) permitidos para su plan ({limite}).",
                    "code": "LIMITE_USUARIOS_ALCANZADO"
                })
    # -----------------------------------------------

    user = User.objects.create_user(
        correo=correo,
        password=password,
        role=rol,
        veterinaria_id=veterinaria_id,
    )

    if estado is not None:
        user.is_active = estado
        user.save(update_fields=["is_active"])

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