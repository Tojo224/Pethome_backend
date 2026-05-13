from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.NotificacionesySeguimiento.models import DispositivoUsuario
from apps.NotificacionesySeguimiento.serializers.dispositivo_usuario_serializer import DispositivoUsuarioSerializer

class DispositivoUsuarioViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DispositivoUsuarioSerializer

    @action(detail=False, methods=["post"], url_path="registrar")
    def registrar_dispositivo(self, request):
        """
        Registra o actualiza un token de FCM para el usuario actual.
        """
        token_fcm = request.data.get("token_fcm")
        plataforma = request.data.get("plataforma", "WEB")

        if not token_fcm:
            return Response({"error": "token_fcm es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Limpieza absoluta: Un token solo puede pertenecer a un usuario en todo el sistema.
        # Si este token ya existe, lo borramos de raíz para evitar cruces.
        DispositivoUsuario.objects.filter(token_fcm=token_fcm).delete()

        # 2. Registrar el nuevo vínculo limpio
        dispositivo = DispositivoUsuario.objects.create(
            token_fcm=token_fcm,
            usuario=request.user,
            veterinaria=request.user.veterinaria,
            plataforma=plataforma,
            activo=True
        )

        return Response(
            {"message": "Dispositivo registrado exitosamente", "id": dispositivo.id_dispositivo},
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="desactivar")
    def desactivar_dispositivo(self, request):
        """
        Marca un token como inactivo (útil para el logout).
        """
        token = request.data.get("token_fcm")
        if not token:
            return Response({"error": "token_fcm es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        
        DispositivoUsuario.objects.filter(token_fcm=token, usuario=request.user).update(activo=False)
        return Response({"message": "Dispositivo desactivado"}, status=status.HTTP_200_OK)
