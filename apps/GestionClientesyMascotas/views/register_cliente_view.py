from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.AutenticacionySeguridad.models import Rol
from apps.AutenticacionySeguridad.serializers.perfil_serializer import (
    PerfilCreateSerializer,
    PerfilSerializer,
)


class RegisterClienteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data.copy()

        try:
            rol_cliente = Rol.objects.get(nombre=Rol.RolName.CLIENT)
            data["id_rol"] = rol_cliente.pk
        except Rol.DoesNotExist:
            return Response(
                {"detail": "El rol de cliente no está configurado en el sistema."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = PerfilCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        perfil = serializer.save()
        return Response(PerfilSerializer(perfil).data, status=status.HTTP_201_CREATED)