import re
import unicodedata

from rest_framework.permissions import BasePermission


ROLE_CLIENT = "CLIENT"
ROLE_ADMIN = "ADMIN"
ROLE_RECEPCIONISTA = "RECEPCIONISTA"
ROLE_VETERINARIAN = "VETERINARIAN"
ROLE_SUPERADMIN = "SUPERADMIN"


_ROLE_ALIASES = {
    "CLIENT": ROLE_CLIENT,
    "CLIENTE": ROLE_CLIENT,
    "ADMIN": ROLE_ADMIN,
    "ADMINISTRADOR": ROLE_ADMIN,
    "RECEPCIONISTA": ROLE_RECEPCIONISTA,
    "VETERINARIAN": ROLE_VETERINARIAN,
    "VETERINARIO": ROLE_VETERINARIAN,
    "SUPERADMIN": ROLE_SUPERADMIN,
}

_PRIVILEGED_ROLES = {
    ROLE_ADMIN,
    ROLE_RECEPCIONISTA,
    ROLE_VETERINARIAN,
    ROLE_SUPERADMIN,
}


def _normalize_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = text.strip("_").upper()
    return text


def normalize_role(value):
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    return _ROLE_ALIASES.get(normalized, normalized)


def get_user_role_name(user):
    if user is None:
        return ""

    if getattr(user, "is_superuser", False):
        return ROLE_SUPERADMIN

    candidates = []

    role_obj = getattr(user, "role", None)
    if role_obj is not None:
        candidates.append(getattr(role_obj, "nombre", None))
        candidates.append(role_obj)

    rol_obj = getattr(user, "rol", None)
    if rol_obj is not None:
        candidates.append(getattr(rol_obj, "nombre", None))
        candidates.append(rol_obj)

    groups = getattr(user, "groups", None)
    if groups is not None:
        try:
            candidates.extend(groups.values_list("name", flat=True))
        except Exception:
            pass

    candidates.extend([
        getattr(user, "role_name", None),
        getattr(user, "rol_name", None),
        getattr(user, "tipo_rol", None),
    ])

    for candidate in candidates:
        normalized = normalize_role(candidate)
        if normalized:
            return normalized

    return ""


def is_client_role(role_name):
    return normalize_role(role_name) == ROLE_CLIENT


def is_admin_role(role_name):
    return normalize_role(role_name) == ROLE_ADMIN


def is_receptionist_role(role_name):
    return normalize_role(role_name) == ROLE_RECEPCIONISTA


def is_veterinarian_role(role_name):
    return normalize_role(role_name) == ROLE_VETERINARIAN


def is_superadmin_role(role_name):
    return normalize_role(role_name) == ROLE_SUPERADMIN


def is_privileged_role(role_name):
    return normalize_role(role_name) in _PRIVILEGED_ROLES


def is_superadmin(user):
    role_name = get_user_role_name(user)
    return bool(getattr(user, "is_superuser", False)) or is_superadmin_role(role_name)


def is_client(user):
    return is_client_role(get_user_role_name(user))


def is_admin(user):
    return is_admin_role(get_user_role_name(user))


def is_receptionist(user):
    return is_receptionist_role(get_user_role_name(user))


def is_veterinarian(user):
    return is_veterinarian_role(get_user_role_name(user))


class HasVeterinariaOrSuperuser(BasePermission):
    message = "No tienes una veterinaria asociada para consultar esta informacion."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True

        return bool(getattr(user, "veterinaria_id", None))


class HasVeterinariaWithoutSuperadmin(BasePermission):
    message = "No tienes permisos para consultar esta informacion."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if is_superadmin(user):
            self.message = "SuperAdmin no tiene acceso a este modulo."
            return False

        if getattr(user, "veterinaria_id", None):
            return True

        self.message = "No tienes una veterinaria asociada para consultar esta informacion."
        return False
