from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema

from apps.AutenticacionySeguridad.models.user import User
from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.GestionarClinicaVeterinaria.serializers.veterinario_serializer import (
    VeterinarioOptionSerializer,
)


class VeterinarioListView(generics.ListAPIView):
    serializer_class = VeterinarioOptionSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Clinica"], responses={200: VeterinarioOptionSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        role_name = (user.role.nombre or "").upper() if user.role_id else ""
        tenant = getattr(self.request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)

        if role_name == RoleEnum.VETERINARIAN.value:
            return (
                User.objects.filter(
                    id_usuario=user.id_usuario,
                    role__nombre=RoleEnum.VETERINARIAN.value,
                    is_active=True,
                    veterinaria_id=tenant_id,
                )
                .select_related("role", "perfil")
                .order_by("perfil__nombre", "correo")
            )

        if role_name != RoleEnum.ADMIN.value:
            raise PermissionDenied("No tienes permiso para consultar veterinarios.")

        return (
            User.objects.filter(
                role__nombre=RoleEnum.VETERINARIAN.value,
                is_active=True,
                veterinaria_id=tenant_id,
            )
            .select_related("role", "perfil")
            .order_by("perfil__nombre", "correo")
        )
