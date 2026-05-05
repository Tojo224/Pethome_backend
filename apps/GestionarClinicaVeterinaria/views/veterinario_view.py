from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission

from apps.AutenticacionySeguridad.models.user import User
from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.GestionarClinicaVeterinaria.serializers.veterinario_serializer import (
    VeterinarioOptionSerializer,
)


class VeterinarioListView(generics.ListAPIView):
    serializer_class = VeterinarioOptionSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_VETERINARIOS"

    @extend_schema(tags=["Clinica"], responses={200: VeterinarioOptionSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        return (
            User.objects.filter(
                role__nombre=RoleEnum.VETERINARIAN.value,
                is_active=True,
                veterinaria_id=tenant_id,
            )
            .select_related("role", "perfil")
            .order_by("perfil__nombre", "correo")
        )