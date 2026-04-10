from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from ..serializers.login_serializer import LoginSerializer
from ..serializers.user_serializer import UserSerializer
from ..services.bitacora_register_service import BitacoraService


def get_tokens_for_user(user):
    """Genera el par de tokens JWT (refresh + access) para el usuario dado."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def _registrar_bitacora_seguro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        # La bitácora no debe bloquear autenticación.
        pass


class LoginView(APIView):
    permission_classes = [AllowAny]
    """
    POST /api/auth/login/
    Body: { "correo": "...", "password": "..." }
    Retorna los tokens JWT y los datos básicos del usuario.
    También crea sesión de servidor para pruebas desde browsable API.
    """

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_login_fallido,
                request,
                request.data.get("correo", ""),
            )
            raise

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)

        # Mantiene sesión en servidor para pruebas desde el backend.
        auth_login(request, user)

        _registrar_bitacora_seguro(
            BitacoraService.registrar_login_exitoso,
            request,
            user,
        )

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "tokens": tokens,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Header: Authorization: Bearer <access_token> o sesión de servidor.
    Body opcional: { "refresh": "<refresh_token>" }
    Si llega refresh, se invalida en blacklist.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        actor = request.user if getattr(request.user, "is_authenticated", False) else None
        detail = "Sesión cerrada correctamente."

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                _registrar_bitacora_seguro(
                    BitacoraService.registrar_evento,
                    accion=BitacoraAccion.LOGOUT,
                    descripcion="Intento de logout con token inválido o expirado.",
                    usuario=actor,
                    request=request,
                    modulo=BitacoraModulo.AUTENTICACION,
                    resultado=BitacoraResultado.FALLO,
                )
                return Response(
                    {"detail": "Token inválido o ya expirado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as exc:
                _registrar_bitacora_seguro(
                    BitacoraService.registrar_evento,
                    accion=BitacoraAccion.LOGOUT,
                    descripcion="Error interno al cerrar sesión.",
                    usuario=actor,
                    request=request,
                    modulo=BitacoraModulo.AUTENTICACION,
                    resultado=BitacoraResultado.FALLO,
                    metadatos={"error": str(exc)},
                )
                raise APIException("No se pudo cerrar sesión en este momento.") from exc
        else:
            detail = "Sesión cerrada correctamente. No se recibió refresh para blacklist."

        auth_logout(request)

        _registrar_bitacora_seguro(
            BitacoraService.registrar_logout,
            request,
            actor,
        )

        return Response({"detail": detail}, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    GET /api/auth/me/
    Header: Authorization: Bearer <access_token>
    Retorna los datos del usuario autenticado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class AuthRootView(APIView):
    """Endpoint informativo para /api/auth/."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "detail": "API de autenticación activa.",
                "endpoints": {
                    "login": "/api/auth/login/",
                    "logout": "/api/auth/logout/",
                    "me": "/api/auth/me/",
                    "bitacora": "/api/auth/bitacora/",
                },
            },
            status=status.HTTP_200_OK,
        )
