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
from ..serializers.auth_context_serializer import AuthContextSerializer
from ..services.auth_context_service import AuthContextService
from ..selectors.componente_selector import ComponenteSelector


def get_tokens_for_user(user):
    """Genera el par de tokens JWT para el usuario dado."""
    refresh = RefreshToken.for_user(user)
    veterinaria = getattr(user, "id_veterinaria", None)
    
    for token in [refresh, refresh.access_token]:
        token["id_usuario"] = user.id_usuario
        token["id_veterinaria"] = user.id_veterinaria_id
        token["is_superuser"] = user.is_superuser

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class LoginView(TenantViewMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="LoginContextResponse",
                    fields={
                        "access": serializers.CharField(),
                        "refresh": serializers.CharField(),
                        "context": AuthContextSerializer(),
                    },
                ),
                description="Login exitoso con contexto SaaS completo.",
            ),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            self.registrar_bitacora(
                accion=BitacoraAccion.LOGIN_FALLIDO,
                descripcion="Intento de inicio de sesión fallido.",
                modulo=BitacoraModulo.AUTENTICACION,
                resultado=BitacoraResultado.FALLO,
                metadatos={"correo": request.data.get("correo", ""), "error": str(exc.detail)}
            )
            raise

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)
        
        # Cargar contexto completo
        plataforma = request.query_params.get("plataforma", "WEB")
        contexto = AuthContextService.get_auth_context(user, plataforma)

        auth_login(request, user)

        self.registrar_bitacora(
            accion=BitacoraAccion.LOGIN_EXITOSO,
            descripcion=f"Inicio de sesión exitoso en {plataforma}.",
            usuario=user,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
            metadatos={"plataforma": plataforma}
        )

        return Response({
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "context": contexto
        }, status=status.HTTP_200_OK)


class MeView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        responses={200: AuthContextSerializer},
        description="Retorna el contexto SaaS completo del usuario autenticado."
    )
    def get(self, request):
        plataforma = request.query_params.get("plataforma", "WEB")
        contexto = AuthContextService.get_auth_context(request.user, plataforma)
        
        self.registrar_bitacora(
            accion=BitacoraAccion.COMPONENTES_CARGADOS,
            descripcion=f"Contexto operativo cargado para {plataforma}.",
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
            metadatos={"plataforma": plataforma}
        )
        
        return Response(contexto, status=status.HTTP_200_OK)


class LogoutView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except: pass

        auth_logout(request)
        self.registrar_bitacora(
            accion=BitacoraAccion.LOGOUT_EXITOSO,
            descripcion="Cierre de sesión exitoso.",
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
        )
        return Response({"detail": "Sesión cerrada correctamente."}, status=status.HTTP_200_OK)


class PublicVeterinariaView(APIView):
    """
    Endpoints públicos para descubrimiento de veterinarias (Móvil).
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Public"],
        description="Obtiene datos públicos de una veterinaria por su slug."
    )
    def get(self, request, slug):
        from ..models.veterinaria import Veterinaria
        vet = Veterinaria.objects.filter(slug=slug, estado=True).first()
        if not vet:
            return Response({"error": "Veterinaria no encontrada."}, status=status.HTTP_404_NOT_FOUND)
            
        return Response({
            "id_veterinaria": vet.id_veterinaria,
            "nombre": vet.nombre,
            "slug": vet.slug,
            "logo": vet.logo if vet.logo else None,
            "direccion": vet.direccion,
            "telefono": vet.telefono
        })


class AuthRootView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "message": "Pethome SaaS Auth API",
            "version": "1.0"
        })
