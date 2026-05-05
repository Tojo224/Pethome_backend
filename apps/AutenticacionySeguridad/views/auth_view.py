from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers

from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from ..mixins.tenant_mixins import TenantViewMixin
from ..serializers.login_serializer import LoginSerializer
from ..serializers.user_serializer import UserSerializer


def get_tokens_for_user(user):
    """Genera el par de tokens JWT (refresh + access) para el usuario dado."""
    refresh = RefreshToken.for_user(user)
    veterinaria = getattr(user, "veterinaria", None)
    vet_id = getattr(user, "veterinaria_id", None)
    vet_slug = getattr(veterinaria, "slug", "") if veterinaria else ""
    vet_nombre = getattr(veterinaria, "nombre", "") if veterinaria else ""
    rol_id = getattr(user, "rol_id", None)
    is_super = getattr(user, "is_superuser", False)

    # Collect basic permissions if possible (assuming user has a property or we can fetch, but we might just leave an empty list or basic summary)
    # The requirement says "y permisos base". We can just omit full permissions to keep token size small and rely on server-side checks.
    permisos_base = []

    for token in [refresh, refresh.access_token]:
        token["id_usuario"] = getattr(user, "id_usuario", None)
        token["id_veterinaria"] = vet_id
        token["veterinaria_slug"] = vet_slug
        token["veterinaria_nombre"] = vet_nombre
        token["id_rol"] = rol_id
        token["is_superuser"] = is_super
        token["permisos_base"] = permisos_base

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }





class LoginView(TenantViewMixin, APIView):
    permission_classes = [AllowAny]
    """
    POST /api/auth/login/
    Body: { "correo": "...", "password": "..." }
    Retorna los tokens JWT y los datos básicos del usuario.
    También crea sesión de servidor para pruebas desde browsable API.
    """

    @extend_schema(
        tags=["Auth"],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="LoginResponse",
                    fields={
                        "access": serializers.CharField(),
                        "refresh": serializers.CharField(),
                        "tokens": inline_serializer(
                            name="TokenPair",
                            fields={
                                "access": serializers.CharField(),
                                "refresh": serializers.CharField(),
                            },
                        ),
                        "user": UserSerializer(),
                    },
                ),
                description="Login exitoso con tokens JWT.",
            ),
            400: OpenApiResponse(description="Credenciales inválidas o cuenta desactivada."),
        },
        examples=[
            OpenApiExample(
                "Login request",
                value={"correo": "admin@demo.com", "password": "secret"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            detail = exc.detail
            error_code = "LOGIN_FALLIDO"
            if isinstance(detail, list) and len(detail) > 0 and isinstance(detail[0], dict):
                error_code = detail[0].get("code", "LOGIN_FALLIDO")
            elif isinstance(detail, dict) and "code" in detail:
                 error_code = detail.get("code")

            self.registrar_bitacora(
                accion=error_code,
                descripcion="Intento de inicio de sesión fallido.",
                modulo=BitacoraModulo.AUTENTICACION,
                resultado=BitacoraResultado.FALLO,
                metadatos={"correo": request.data.get("correo", ""), "error": str(detail)}
            )
            raise

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)

        # Mantiene sesión en servidor para pruebas desde el backend.
        auth_login(request, user)

        self.registrar_bitacora(
            accion=BitacoraAccion.LOGIN,
            descripcion="Inicio de sesión exitoso.",
            usuario=user,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
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


class LogoutView(TenantViewMixin, APIView):
    """
    POST /api/auth/logout/
    Header: Authorization: Bearer <access_token> o sesión de servidor.
    Body opcional: { "refresh": "<refresh_token>" }
    Si llega refresh, se invalida en blacklist.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        request=inline_serializer(
            name="LogoutRequest",
            fields={"refresh": serializers.CharField(required=False)},
        ),
        responses={
            200: inline_serializer(
                name="LogoutResponse",
                fields={"detail": serializers.CharField()},
            ),
            400: OpenApiResponse(description="Token inválido o expirado."),
        },
    )
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
                    accion="LOGOUT_TOKEN_INVALIDO",
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
                    accion="LOGOUT_FALLIDO",
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
        if hasattr(request, "tenant"):
            request.tenant = None

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.LOGOUT,
            descripcion="Cierre de sesión exitoso.",
            usuario=actor,
            request=request,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
        )

        return Response({"detail": detail}, status=status.HTTP_200_OK)


class MeView(TenantViewMixin, APIView):
    """
    GET /api/auth/me/
    Header: Authorization: Bearer <access_token>
    Retorna los datos del usuario autenticado.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        responses={200: UserSerializer},
    )
    def get(self, request):
        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.VISUALIZAR,
            descripcion="Consulta de datos del usuario autenticado.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(request.user, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
        )
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class AuthRootView(APIView):
    """Endpoint informativo para /api/auth/."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        responses={
            200: inline_serializer(
                name="AuthRootResponse",
                fields={
                    "detail": serializers.CharField(),
                    "endpoints": inline_serializer(
                        name="AuthRootEndpoints",
                        fields={
                            "login": serializers.CharField(),
                            "logout": serializers.CharField(),
                            "me": serializers.CharField(),
                            "bitacora": serializers.CharField(),
                        },
                    ),
                },
            )
        },
    )
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
