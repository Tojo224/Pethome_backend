from rest_framework.permissions import BasePermission

from apps.AutenticacionySeguridad.enums.roles import RoleEnum


class IsAdminOrVeterinarianForSales(BasePermission):
    message = "No tienes permisos para registrar o consultar ventas presenciales."

    allowed_roles = {
        RoleEnum.ADMIN.value,
        RoleEnum.VETERINARIAN.value,
    }

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True

        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        return role_name in self.allowed_roles


class IsClientForMobileCart(BasePermission):
    message = "Solo clientes autenticados del tenant actual pueden gestionar el carrito móvil."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return False

        tenant = getattr(request, "tenant", None)
        tenant_id = getattr(tenant, "id", None) or getattr(user, "veterinaria_id", None)
        if not tenant_id:
            return False

        if getattr(user, "veterinaria_id", None) != tenant_id:
            return False

        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        return role_name == RoleEnum.CLIENT.value
