from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer

from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from ..mixins.tenant_mixins import TenantViewMixin
from ..models import Perfil, Rol, User, Veterinaria
from ..serializers.auth_context_serializer import AuthContextSerializer
from ..serializers.login_serializer import (
    LoginSerializer,
    MobileLoginSerializer,
    MobileRegisterSerializer,
    get_active_suscripcion,
)
from ..services.auth_context_service import AuthContextService
from ..services.base_access_seed_service import BaseAccessSeedService


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    for token in [refresh, refresh.access_token]:
        token["id_usuario"] = user.id_usuario
        token["id_rol"] = user.role_id
        token["id_veterinaria"] = user.veterinaria_id
        token["is_superuser"] = user.is_superuser
        token["permisos_base"] = []
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


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
                description="Login exitoso con contexto SaaS.",
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
                descripcion="Intento de login web fallido.",
                modulo=BitacoraModulo.AUTENTICACION,
                resultado=BitacoraResultado.FALLO,
                metadatos={"correo": request.data.get("correo", ""), "error": str(exc.detail)},
            )
            raise

        user = serializer.validated_data["user"]
        plataforma = serializer.validated_data.get("plataforma", "WEB")
        tokens = get_tokens_for_user(user)
        context = AuthContextService.get_auth_context(user, plataforma)
        auth_login(request, user)

        self.registrar_bitacora(
            accion=BitacoraAccion.LOGIN_EXITOSO,
            descripcion=f"Login web exitoso en plataforma {plataforma}.",
            usuario=user,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
            metadatos={"plataforma": plataforma},
        )

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "tokens": {"access": tokens["access"], "refresh": tokens["refresh"]},
                "user": context.get("usuario", {}),
                "context": context,
            },
            status=status.HTTP_200_OK,
        )


class MobileLoginView(TenantViewMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=MobileLoginSerializer,
        responses={200: OpenApiResponse(description="Login movil exitoso con contexto SaaS.")},
    )
    def post(self, request):
        serializer = MobileLoginSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            self.registrar_bitacora(
                accion=BitacoraAccion.LOGIN_FALLIDO,
                descripcion="Intento de login movil fallido.",
                modulo=BitacoraModulo.AUTENTICACION,
                resultado=BitacoraResultado.FALLO,
                metadatos={"correo": request.data.get("correo", ""), "error": str(exc.detail)},
            )
            raise

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)
        context = AuthContextService.get_auth_context(user, "MOVIL")
        auth_login(request, user)

        self.registrar_bitacora(
            accion=BitacoraAccion.LOGIN_EXITOSO,
            descripcion="Login movil exitoso.",
            usuario=user,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "plataforma": "MOVIL",
                "slug_veterinaria": serializer.validated_data.get("slug_veterinaria"),
            },
        )

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "tokens": {"access": tokens["access"], "refresh": tokens["refresh"]},
                "user": context.get("usuario", {}),
                "context": context,
            },
            status=status.HTTP_200_OK,
        )


class MobileRegisterView(TenantViewMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=MobileRegisterSerializer,
        responses={201: OpenApiResponse(description="Registro movil exitoso.")},
    )
    @transaction.atomic
    def post(self, request):
        serializer = MobileRegisterSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            self.registrar_bitacora(
                accion=BitacoraAccion.CLIENTE_CREADO,
                descripcion="Fallo de validacion en registro movil.",
                modulo=BitacoraModulo.CLIENTES,
                resultado=BitacoraResultado.FALLO,
                metadatos={"error": str(exc.detail)},
            )
            raise

        data = serializer.validated_data
        veterinaria = Veterinaria.objects.filter(
            slug=data["slug_veterinaria"], estado=True
        ).first()
        if not veterinaria:
            raise ValidationError(
                {"detail": "Veterinaria no encontrada o inactiva.", "code": "REGISTRO_VETERINARIA_INVALIDA"}
            )

        if not veterinaria.permite_auto_registro_clientes:
            raise ValidationError(
                {"detail": "Esta veterinaria no permite auto-registro.", "code": "AUTO_REGISTRO_DESHABILITADO"}
            )

        suscripcion = get_active_suscripcion(veterinaria.id_veterinaria)
        if not suscripcion or suscripcion.estado_suscripcion in {"VENCIDA", "SUSPENDIDA", "CANCELADA"}:
            raise ValidationError(
                {"detail": "La veterinaria no tiene suscripcion valida.", "code": "REGISTRO_SUSCRIPCION_INVALIDA"}
            )
        if not suscripcion.plan.permite_app_movil:
            raise ValidationError(
                {"detail": "El plan no permite app movil.", "code": "REGISTRO_APP_MOVIL_NO_PERMITIDA"}
            )

        if User.objects.filter(correo=data["correo"]).exists():
            raise ValidationError({"correo": ["Este correo ya esta registrado."]})

        rol_client = Rol.objects.filter(nombre="CLIENT").first()
        if not rol_client:
            raise ValidationError(
                {"detail": "Rol CLIENT no configurado en el sistema.", "code": "ROL_CLIENT_NO_CONFIGURADO"}
            )

        user = User.objects.create_user(
            correo=data["correo"],
            password=data["password"],
            role=rol_client,
            veterinaria=veterinaria,
            is_active=True,
        )
        Perfil.objects.create(
            usuario=user,
            nombre=data["nombre"],
            telefono=data.get("telefono", ""),
            direccion=data.get("direccion", ""),
            estado=True,
        )

        BaseAccessSeedService.seed_base_groups_for_veterinaria(veterinaria)
        BaseAccessSeedService.seed_base_permissions_for_veterinaria(veterinaria)
        BaseAccessSeedService.assign_existing_users_to_base_groups(veterinaria)

        tokens = get_tokens_for_user(user)
        context = AuthContextService.get_auth_context(user, "MOVIL")
        auth_login(request, user)

        self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_CREADO,
            descripcion="Registro movil de cliente exitoso.",
            usuario=user,
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="User",
            entidad_id=user.id_usuario,
            resultado=BitacoraResultado.EXITO,
            metadatos={"slug_veterinaria": veterinaria.slug, "plataforma": "MOVIL"},
        )

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "tokens": {"access": tokens["access"], "refresh": tokens["refresh"]},
                "user": context.get("usuario", {}),
                "context": context,
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"], responses={200: AuthContextSerializer})
    def get(self, request):
        plataforma = str(request.query_params.get("plataforma", "WEB")).upper()
        context = AuthContextService.get_auth_context(request.user, plataforma)

        self.registrar_bitacora(
            accion=BitacoraAccion.COMPONENTES_CARGADOS,
            descripcion=f"Contexto operativo cargado para {plataforma}.",
            usuario=request.user,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
            metadatos={"plataforma": plataforma},
        )
        user_data = context.get("usuario", {})
        return Response(
            {
                "id_usuario": user_data.get("id_usuario"),
                "correo": user_data.get("correo"),
                "id_veterinaria": user_data.get("id_veterinaria"),
                "rol": user_data.get("rol"),
                "is_superuser": user_data.get("is_superuser"),
                "context": context,
            },
            status=status.HTTP_200_OK,
        )


class ComponentesView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plataforma = str(request.query_params.get("plataforma", "WEB")).upper()
        context = AuthContextService.get_auth_context(request.user, plataforma)
        return Response({"componentes": context.get("componentes", [])}, status=status.HTTP_200_OK)


class LogoutView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        detail_message = "Sesion cerrada correctamente."
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except Exception:
                return Response(
                    {"detail": "Token invalido o ya invalidado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            detail_message = "No se recibió refresh; se cerró sesión de servidor."

        auth_logout(request)

        self.registrar_bitacora(
            accion=BitacoraAccion.LOGOUT_EXITOSO,
            descripcion="Cierre de sesion exitoso.",
            usuario=request.user,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
        )
        return Response({"detail": detail_message}, status=status.HTTP_200_OK)


class PublicVeterinariaListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Public"], description="Lista veterinarias publicas para flujo movil.")
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        qs = Veterinaria.objects.filter(estado=True)
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(slug__icontains=search))

        data = []
        for vet in qs.order_by("nombre")[:100]:
            suscripcion = get_active_suscripcion(vet.id_veterinaria)
            if not suscripcion:
                continue
            if suscripcion.estado_suscripcion not in {"ACTIVA", "PRUEBA"}:
                continue
            if not suscripcion.plan.permite_app_movil:
                continue
            data.append(
                {
                    "id_veterinaria": vet.id_veterinaria,
                    "nombre": vet.nombre,
                    "slug": vet.slug,
                    "logo": vet.logo,
                    "direccion": vet.direccion,
                }
            )
        return Response(data, status=status.HTTP_200_OK)


class PublicVeterinariaView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Public"], description="Detalle publico de veterinaria por slug.")
    def get(self, request, slug):
        vet = Veterinaria.objects.filter(slug=slug, estado=True).first()
        if not vet:
            return Response({"error": "Veterinaria no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        suscripcion = get_active_suscripcion(vet.id_veterinaria)
        if not suscripcion or suscripcion.estado_suscripcion not in {"ACTIVA", "PRUEBA"}:
            return Response({"error": "Veterinaria no disponible."}, status=status.HTTP_404_NOT_FOUND)
        if not suscripcion.plan.permite_app_movil:
            return Response({"error": "Veterinaria no habilitada para movil."}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "id_veterinaria": vet.id_veterinaria,
                "nombre": vet.nombre,
                "slug": vet.slug,
                "logo": vet.logo if vet.logo else None,
                "direccion": vet.direccion,
                "telefono": vet.telefono,
            }
        )


class AuthRootView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"message": "Pethome SaaS Auth API", "version": "1.1"})

