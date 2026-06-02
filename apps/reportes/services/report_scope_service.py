from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied


def resolve_scope(user, id_veterinaria=None):
    """Determina el alcance de la consulta según el rol del usuario.

    Retorna un dict con 'veterinaria' (modelo o None) y 'global' (bool).
    Lanza PermissionDenied si el usuario no puede acceder.
    """
    role_name = (getattr(getattr(user, "role", None), "nombre", None) or "").upper()

    if getattr(user, "is_superuser", False) or role_name == "SUPERADMIN":
        if id_veterinaria:
            from apps.AutenticacionySeguridad.models.veterinaria import Veterinaria

            vet = get_object_or_404(Veterinaria, id_veterinaria=id_veterinaria)
            return {"veterinaria": vet, "global": False}
        return {"veterinaria": None, "global": True}

    if role_name in {"ADMIN", "VETERINARIAN"}:
        # user must have veterinaria assigned
        if not getattr(user, "veterinaria", None):
            raise PermissionDenied("Usuario no asociado a una veterinaria")
        # ignore provided id_veterinaria if different
        return {"veterinaria": user.veterinaria, "global": False}

    raise PermissionDenied("Rol no autorizado para reportes")
