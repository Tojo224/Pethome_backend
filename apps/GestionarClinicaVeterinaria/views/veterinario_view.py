from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.AutenticacionySeguridad.models.user import User
from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.GestionarClinicaVeterinaria.serializers.veterinario_serializer import (
    VeterinarioOptionSerializer,
)


class VeterinarioListView(generics.ListAPIView):
    serializer_class = VeterinarioOptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            User.objects.filter(
                role__nombre=RoleEnum.VETERINARIAN.value,
                is_active=True,
            )
            .select_related("role", "perfil")
            .order_by("perfil__nombre", "correo")
        )