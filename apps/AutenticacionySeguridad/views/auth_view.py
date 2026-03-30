from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from apps.AutenticacionySeguridad.serializers.login_serializer import LoginSerializer
from apps.AutenticacionySeguridad.serializers.user_serializer import UserSerializer


def get_tokens_for_user(user):
    """Genera el par de tokens JWT (refresh + access) para el usuario dado."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { "correo": "...", "password": "..." }
    Retorna los tokens JWT y los datos básicos del usuario.
    """

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)

        return Response(
            {
                "tokens": tokens,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Header: Authorization: Bearer <access_token>
    Body: { "refresh": "<refresh_token>" }
    Invalida el refresh token en la blacklist.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "El campo 'refresh' es requerido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Sesión cerrada correctamente."},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"detail": "Token inválido o ya expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(APIView):
    """
    GET /api/auth/me/
    Header: Authorization: Bearer <access_token>
    Retorna los datos del usuario autenticado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )
