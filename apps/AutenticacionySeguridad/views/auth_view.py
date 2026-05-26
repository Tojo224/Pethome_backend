from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import json
import logging
import os
import secrets
import threading
from decouple import config
from rest_framework import serializers, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer

from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from ..mixins.tenant_mixins import TenantViewMixin
from ..models import (
    BillingDemoEvent,
    GrupoUsuario,
    Perfil,
    PlanSuscripcion,
    Rol,
    Suscripcion,
    User,
    UsuarioGrupo,
    Veterinaria,
)
from ..serializers.auth_context_serializer import AuthContextSerializer
from ..serializers.login_serializer import (
    LoginSerializer,
    MobileLoginSerializer,
    MobileRegisterSerializer,
    get_active_suscripcion,
)
from ..serializers.password_security_serializer import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from ..services.auth_context_service import AuthContextService
from ..services.base_access_seed_service import BaseAccessSeedService
from ..services.auth_security_service import (
    change_user_password,
    consume_password_reset_token,
    create_password_reset_token,
    get_password_reset_expiration_minutes,
    get_user_for_login,
    reset_user_password,
    send_password_reset_email,
)

logger = logging.getLogger(__name__)

try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None


def _seed_tenant_async(veterinaria_id: int) -> None:
    """
    Ejecuta seed de RBAC fuera del request para evitar bloquear
    endpoints pÃƒÂºblicos de onboarding.
    """
    try:
        veterinaria = Veterinaria.objects.filter(id_veterinaria=veterinaria_id).first()
        if not veterinaria:
            return
        BaseAccessSeedService.seed_global_components()
        BaseAccessSeedService.seed_for_veterinarias(veterinarias=[veterinaria], assign_existing=True)
    except Exception:
        logger.exception("Fallo seed async para veterinaria %s", veterinaria_id)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    for token in [refresh, refresh.access_token]:
        token["id_usuario"] = user.id_usuario
        token["id_rol"] = user.role_id
        token["id_veterinaria"] = user.veterinaria_id
        token["is_superuser"] = user.is_superuser
        token["permisos_base"] = []
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def safe_session_login(request, user):
    """
    Intenta iniciar sesiÃƒÂ³n en la sesiÃƒÂ³n Django solo si existe soporte de sesiÃƒÂ³n.
    El login principal del sistema usa JWT, asÃƒÂ­ que esta llamada no debe romper
    la respuesta del API si no hay session middleware disponible.
    """
    session = getattr(request, "session", None)
    if session is None:
        return

    try:
        auth_login(request, user)
    except Exception:
        # No interrumpir el login JWT si la sesiÃƒÂ³n no puede persistirse.
        logger.exception("No se pudo crear sesiÃƒÂ³n Django durante login JWT")


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
        except APIException as exc:
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
        safe_session_login(request, user)

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
        except APIException as exc:
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
        safe_session_login(request, user)

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

        # Registro movil debe ser liviano: no reseed global por cada cliente nuevo.
        # Solo asegura grupos/permisos base del tenant y asigna CLIENT_BASE al usuario creado.
        BaseAccessSeedService.seed_for_veterinarias(
            veterinarias=[veterinaria],
            assign_existing=False,
        )
        grupo_client_base, _ = GrupoUsuario.objects.get_or_create(
            veterinaria=veterinaria,
            rol_base="CLIENT",
            defaults={
                "nombre": "CLIENT_BASE",
                "descripcion": "Grupo base automatico para clientes moviles.",
                "estado": True,
                "es_base": True,
            },
        )
        if not grupo_client_base.estado:
            grupo_client_base.estado = True
            grupo_client_base.save(update_fields=["estado"])

        UsuarioGrupo.objects.get_or_create(
            usuario=user,
            grupo=grupo_client_base,
            defaults={"estado": True},
        )

        tokens = get_tokens_for_user(user)
        context = AuthContextService.get_auth_context(user, "MOVIL")
        safe_session_login(request, user)

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
            detail_message = "No se recibiÃƒÂ³ refresh; se cerrÃƒÂ³ sesiÃƒÂ³n de servidor."

        auth_logout(request)

        self.registrar_bitacora(
            accion=BitacoraAccion.LOGOUT_EXITOSO,
            descripcion="Cierre de sesion exitoso.",
            usuario=request.user,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
        )
        return Response({"detail": detail_message}, status=status.HTTP_200_OK)


class ForgotPasswordView(TenantViewMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=ForgotPasswordSerializer,
        responses={200: OpenApiResponse(description="Respuesta generica de recuperacion.")},
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        correo = serializer.validated_data["correo"]
        user = get_user_for_login(correo)

        if user and user.is_active:
            try:
                token = create_password_reset_token(user)
                send_password_reset_email(user, token)
            except Exception as exc:
                logger.exception("Fallo el envio del correo de recuperacion para %s", correo)
                self.registrar_bitacora(
                    accion=BitacoraAccion.CAMBIO_PASSWORD,
                    descripcion="Fallo el envio del correo de recuperacion.",
                    usuario=user,
                    modulo=BitacoraModulo.AUTENTICACION,
                    resultado=BitacoraResultado.FALLO,
                    metadatos={"correo": correo, "error": str(exc)},
                )
            else:
                self.registrar_bitacora(
                    accion=BitacoraAccion.CAMBIO_PASSWORD,
                    descripcion="Se genero token de recuperacion de contrasena.",
                    usuario=user,
                    modulo=BitacoraModulo.AUTENTICACION,
                    resultado=BitacoraResultado.EXITO,
                    metadatos={
                        "correo": correo,
                        "expira_en_minutos": get_password_reset_expiration_minutes(),
                    },
                )

        return Response(
            {"detail": "Si el correo existe, se enviara un enlace de recuperacion."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(TenantViewMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=ResetPasswordSerializer,
        responses={200: OpenApiResponse(description="Contrasena restablecida.")},
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = consume_password_reset_token(serializer.validated_data["token"])
        reset_user_password(token, serializer.validated_data["nueva_password"])

        self.registrar_bitacora(
            accion=BitacoraAccion.CAMBIO_PASSWORD,
            descripcion="Contrasena restablecida mediante token.",
            usuario=token.usuario,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
            metadatos={"reset_por_token": True},
        )

        return Response(
            {"detail": "La contrasena fue restablecida correctamente."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Contrasena cambiada.")},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        change_user_password(
            user=request.user,
            password_actual=serializer.validated_data["password_actual"],
            nueva_password=serializer.validated_data["nueva_password"],
        )

        self.registrar_bitacora(
            accion=BitacoraAccion.CAMBIO_PASSWORD,
            descripcion="Cambio de contrasena autenticado.",
            usuario=request.user,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
            metadatos={"change_password": True, "fecha": timezone.now().isoformat()},
        )

        return Response(
            {"detail": "La contrasena fue actualizada correctamente."},
            status=status.HTTP_200_OK,
        )


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


class TrialSignupSerializer(serializers.Serializer):
    veterinaria_nombre = serializers.CharField(max_length=200)
    veterinaria_slug = serializers.SlugField(max_length=200)
    veterinaria_correo = serializers.EmailField(required=False, allow_blank=True)
    veterinaria_telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)
    veterinaria_direccion = serializers.CharField(required=False, allow_blank=True)
    admin_nombre = serializers.CharField(max_length=150)
    admin_correo = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True, min_length=8)
    admin_telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    admin_direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_veterinaria_slug(self, value):
        slug = (value or "").strip().lower()
        if Veterinaria.objects.filter(slug=slug).exists():
            raise serializers.ValidationError("El slug ya estÃƒÂ¡ en uso.")
        return slug

    def validate_admin_correo(self, value):
        if User.objects.filter(correo=value).exists():
            raise serializers.ValidationError("El correo del administrador ya estÃƒÂ¡ registrado.")
        return value


class DemoCheckoutStartSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    # Datos para compra directa (cuando aÃƒÂºn no existe tenant)
    veterinaria_nombre = serializers.CharField(max_length=200, required=False)
    veterinaria_slug = serializers.SlugField(max_length=200, required=False)
    veterinaria_correo = serializers.EmailField(required=False, allow_blank=True)
    veterinaria_telefono = serializers.CharField(max_length=30, required=False, allow_blank=True)
    veterinaria_direccion = serializers.CharField(required=False, allow_blank=True)
    admin_nombre = serializers.CharField(max_length=150, required=False)
    admin_correo = serializers.EmailField(required=False)
    admin_password = serializers.CharField(write_only=True, min_length=8, required=False)
    admin_telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    admin_direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_plan_id(self, value):
        if not PlanSuscripcion.objects.filter(id_plan=value, estado=True).exists():
            raise serializers.ValidationError("Plan invÃ¡lido o inactivo.")
        return value

    def validate_veterinaria_slug(self, value):
        slug = (value or "").strip().lower()
        if Veterinaria.objects.filter(slug=slug).exists():
            raise serializers.ValidationError("El slug ya estÃ¡ en uso.")
        return slug

    def validate_admin_correo(self, value):
        if User.objects.filter(correo=value).exists():
            raise serializers.ValidationError("El correo del administrador ya estÃ¡ registrado.")
        return value

    def validate_admin_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class DemoCheckoutConfirmSerializer(serializers.Serializer):
    checkout_token = serializers.CharField(max_length=120)


def _get_role_or_raise(role_name: str):
    role = Rol.objects.filter(nombre=role_name).first()
    if not role:
        raise ValidationError({"detail": f"Rol {role_name} no configurado.", "code": "ROL_NO_CONFIGURADO"})
    return role


def _create_subscription(veterinaria, plan, estado, fecha_inicio, fecha_fin=None, renovacion_automatica=False):
    Suscripcion.objects.filter(
        veterinaria=veterinaria,
        estado_suscripcion__in=["ACTIVA", "PRUEBA"],
    ).update(
        estado_suscripcion="CANCELADA",
        fecha_fin=fecha_inicio,
        renovacion_automatica=False,
    )

    return Suscripcion.objects.create(
        veterinaria=veterinaria,
        plan=plan,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado_suscripcion=estado,
        renovacion_automatica=renovacion_automatica,
        metodo_pago="DEMO",
    )


def _stripe_enabled():
    return bool(stripe) and bool(config("STRIPE_SECRET_KEY", default="")) and bool(config("STRIPE_WEBHOOK_SECRET", default=""))


def _stripe_create_checkout_session(*, event: BillingDemoEvent, plan: PlanSuscripcion):
    stripe_secret_key = config("STRIPE_SECRET_KEY", default="")
    if not stripe or not stripe_secret_key:
        return None

    stripe.api_key = stripe_secret_key
    frontend_success_url = config("STRIPE_SUCCESS_URL", default="http://localhost:3000/billing/success")
    frontend_cancel_url = config("STRIPE_CANCEL_URL", default="http://localhost:3000/billing/cancel")
    currency = (config("STRIPE_CURRENCY", default="usd") or "usd").lower()

    try:
        amount = Decimal(str(plan.precio_mensual or 0))
    except (InvalidOperation, TypeError):
        amount = Decimal("0")
    amount_cents = int(amount * 100)

    return stripe.checkout.Session.create(
        mode="payment",
        success_url=f"{frontend_success_url}?checkout_token={event.checkout_token}",
        cancel_url=f"{frontend_cancel_url}?checkout_token={event.checkout_token}",
        client_reference_id=event.checkout_token,
        metadata={
            "checkout_token": event.checkout_token,
            "plan_id": str(event.plan_id),
            "event_type": event.event_type,
        },
        payment_intent_data={
            "metadata": {
                "checkout_token": event.checkout_token,
                "plan_id": str(event.plan_id),
            }
        },
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": f"Suscripcion {plan.nombre}",
                        "description": "PetHome SaaS",
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
    )


def _mark_event_as_paid(
    event: BillingDemoEvent,
    *,
    stripe_session_id=None,
    stripe_payment_intent_id=None,
    amount=None,
    currency=None,
    stripe_event_id=None,
):
    update_fields = ["status", "updated_at"]
    event.status = BillingDemoEvent.EventStatus.PAID

    if stripe_session_id:
        event.stripe_session_id = stripe_session_id
        update_fields.append("stripe_session_id")
    if stripe_payment_intent_id:
        event.stripe_payment_intent_id = stripe_payment_intent_id
        update_fields.append("stripe_payment_intent_id")
    if amount is not None:
        event.amount = Decimal(amount) / Decimal(100)
        update_fields.append("amount")
    if currency:
        event.currency = (currency or "").lower()
        update_fields.append("currency")
    if stripe_event_id:
        event.stripe_event_id = stripe_event_id
        update_fields.append("stripe_event_id")

    event.save(update_fields=update_fields)


def _resolve_pending_checkout_fallback(*, obj_type, obj_amount_total, obj_currency):
    """
    Fallback para entornos donde el frontend no reutiliza el checkout_url del backend.
    Intenta asociar el evento al checkout PENDING más reciente y compatible.
    """
    if obj_type != "checkout.session":
        return None

    pending = (
        BillingDemoEvent.objects.filter(
            status=BillingDemoEvent.EventStatus.PENDING,
            payment_mode="STRIPE",
        )
        .select_related("plan")
        .order_by("-created_at")
    )

    currency = (obj_currency or "").lower()
    for candidate in pending[:10]:
        try:
            expected_amount = int(Decimal(str(candidate.plan.precio_mensual or 0)) * 100)
        except (InvalidOperation, TypeError):
            expected_amount = 0

        if obj_amount_total == expected_amount and (
            not currency or not candidate.currency or candidate.currency == currency
        ):
            return candidate

    return pending.first()


class PublicTrialSignupView(TenantViewMixin, APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = TrialSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        trial_plan = (
            PlanSuscripcion.objects.filter(nombre__iexact="TRIAL", estado=True).order_by("id_plan").first()
            or PlanSuscripcion.objects.filter(estado=True).order_by("precio_mensual", "id_plan").first()
        )
        if not trial_plan:
            raise ValidationError({"detail": "No existe un plan disponible para prueba."})

        role_admin = _get_role_or_raise("ADMIN")

        veterinaria = Veterinaria.objects.create(
            nombre=data["veterinaria_nombre"].strip(),
            slug=data["veterinaria_slug"],
            correo=(data.get("veterinaria_correo") or data["admin_correo"]).strip(),
            telefono=(data.get("veterinaria_telefono") or data.get("admin_telefono") or "").strip(),
            direccion=(data.get("veterinaria_direccion") or "").strip(),
            estado=True,
        )

        admin_user = User.objects.create_user(
            correo=data["admin_correo"],
            password=data["admin_password"],
            role=role_admin,
            veterinaria=veterinaria,
            is_active=True,
        )
        Perfil.objects.create(
            usuario=admin_user,
            nombre=data["admin_nombre"].strip(),
            telefono=(data.get("admin_telefono") or "").strip(),
            direccion=(data.get("admin_direccion") or "").strip(),
            estado=True,
        )

        veterinaria.owner_user = admin_user
        veterinaria.save(update_fields=["owner_user"])

        transaction.on_commit(
            lambda: threading.Thread(
                target=_seed_tenant_async,
                args=(veterinaria.id_veterinaria,),
                daemon=True,
            ).start()
        )

        fecha_inicio = timezone.localdate()
        # Trial fijo de 7 dias (no configurable por cliente/frontend).
        fecha_fin = fecha_inicio + timedelta(days=7)
        _create_subscription(
            veterinaria=veterinaria,
            plan=trial_plan,
            estado="PRUEBA",
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            renovacion_automatica=False,
        )

        tokens = get_tokens_for_user(admin_user)
        context = AuthContextService.get_auth_context(admin_user, "WEB")

        return Response(
            {
                "detail": "Prueba creada correctamente.",
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "tokens": {"access": tokens["access"], "refresh": tokens["refresh"]},
                "user": context.get("usuario", {}),
                "context": context,
            },
            status=status.HTTP_201_CREATED,
        )


class PublicDemoCheckoutStartView(TenantViewMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DemoCheckoutStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        required_fields = [
            "veterinaria_nombre",
            "veterinaria_slug",
            "admin_nombre",
            "admin_correo",
            "admin_password",
        ]
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            raise ValidationError({"detail": f"Faltan campos requeridos para compra directa: {', '.join(missing)}"})

        if Veterinaria.objects.filter(slug=data["veterinaria_slug"]).exists():
            raise ValidationError({"veterinaria_slug": ["El slug ya estÃ¡ en uso."]})
        if User.objects.filter(correo=data["admin_correo"]).exists():
            raise ValidationError({"admin_correo": ["El correo del administrador ya estÃ¡ registrado."]})

        checkout_token = secrets.token_urlsafe(32)
        plan = PlanSuscripcion.objects.get(id_plan=data["plan_id"])
        event = BillingDemoEvent.objects.create(
            checkout_token=checkout_token,
            event_type=BillingDemoEvent.EventType.DIRECT_PURCHASE,
            status=BillingDemoEvent.EventStatus.PENDING,
            plan=plan,
            payload={
                "veterinaria_nombre": data["veterinaria_nombre"],
                "veterinaria_slug": data["veterinaria_slug"],
                "veterinaria_correo": data.get("veterinaria_correo", ""),
                "veterinaria_telefono": data.get("veterinaria_telefono", ""),
                "veterinaria_direccion": data.get("veterinaria_direccion", ""),
                "admin_nombre": data["admin_nombre"],
                "admin_correo": data["admin_correo"],
                "admin_password": data["admin_password"],
                "admin_telefono": data.get("admin_telefono", ""),
                "admin_direccion": data.get("admin_direccion", ""),
            },
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        checkout_url = None
        if _stripe_enabled():
            session = _stripe_create_checkout_session(event=event, plan=plan)
            if session:
                event.stripe_session_id = session.id
                event.payment_mode = "STRIPE"
                event.save(update_fields=["stripe_session_id", "payment_mode", "updated_at"])
                checkout_url = getattr(session, "url", None)
        else:
            event.status = BillingDemoEvent.EventStatus.STARTED
            event.payment_mode = "DEMO"
            event.save(update_fields=["status", "payment_mode", "updated_at"])

        return Response(
            {
                "checkout_token": checkout_token,
                "event_id": event.id_billing_demo_event,
                "expires_at": event.expires_at,
                "payment_mode": event.payment_mode,
                "checkout_url": checkout_url,
                "detail": "Checkout iniciado.",
            },
            status=status.HTTP_201_CREATED,
        )


class StripeWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        stripe_secret_key = config("STRIPE_SECRET_KEY", default="")
        stripe_webhook_secret = config("STRIPE_WEBHOOK_SECRET", default="")
        if not stripe or not stripe_secret_key or not stripe_webhook_secret:
            return Response({"detail": "Stripe no configurado."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        stripe.api_key = stripe_secret_key

        try:
            stripe_event = stripe.Webhook.construct_event(payload, sig_header, stripe_webhook_secret)
        except Exception:
            return Response({"detail": "Firma de webhook inválida."}, status=status.HTTP_400_BAD_REQUEST)

        # Leer el payload JSON crudo evita diferencias entre versiones del SDK.
        # La firma ya fue validada por construct_event.
        event_dict = json.loads(payload.decode("utf-8"))
        event_type = event_dict.get("type")
        event_id = event_dict.get("id")
        obj = event_dict.get("data", {}).get("object", {}) or {}

        obj_type = obj.get("object")
        obj_id = obj.get("id")
        obj_payment_intent = obj.get("payment_intent")
        obj_amount_total = obj.get("amount_total")
        obj_amount = obj.get("amount")
        obj_currency = obj.get("currency")
        obj_metadata = obj.get("metadata") or {}
        token = obj_metadata.get("checkout_token") or obj.get("client_reference_id")

        checkout = None
        if token:
            checkout = BillingDemoEvent.objects.filter(checkout_token=token).first()
        if not checkout and obj_type == "checkout.session":
            checkout = BillingDemoEvent.objects.filter(stripe_session_id=obj_id).first()
        if not checkout:
            payment_intent_id = obj_payment_intent or obj_id
            if payment_intent_id:
                checkout = BillingDemoEvent.objects.filter(stripe_payment_intent_id=payment_intent_id).first()

        if not checkout:
            checkout = _resolve_pending_checkout_fallback(
                obj_type=obj_type,
                obj_amount_total=obj_amount_total,
                obj_currency=obj_currency,
            )

        if not checkout:
            logger.warning(
                "Stripe webhook sin checkout asociado. type=%s event_id=%s obj_type=%s obj_id=%s token=%s pi=%s",
                event_type,
                event_id,
                obj_type,
                obj_id,
                token,
                obj_payment_intent,
            )
            return Response({"detail": "Webhook recibido sin checkout asociado."}, status=status.HTTP_200_OK)

        if checkout.status == BillingDemoEvent.EventStatus.CONFIRMED:
            return Response({"detail": "Checkout ya confirmado."}, status=status.HTTP_200_OK)

        if event_type == "checkout.session.completed":
            _mark_event_as_paid(
                checkout,
                stripe_session_id=obj_id,
                stripe_payment_intent_id=obj_payment_intent,
                amount=obj_amount_total,
                currency=obj_currency,
                stripe_event_id=event_id,
            )
        elif event_type == "payment_intent.succeeded":
            _mark_event_as_paid(
                checkout,
                stripe_payment_intent_id=obj_id,
                amount=obj_amount,
                currency=obj_currency,
                stripe_event_id=event_id,
            )
        elif event_type == "payment_intent.payment_failed":
            checkout.status = BillingDemoEvent.EventStatus.FAILED
            checkout.stripe_payment_intent_id = obj_id
            checkout.stripe_event_id = event_id
            checkout.save(update_fields=["status", "stripe_payment_intent_id", "stripe_event_id", "updated_at"])

        return Response({"detail": "Webhook procesado."}, status=status.HTTP_200_OK)

class PublicDemoCheckoutConfirmView(TenantViewMixin, APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = DemoCheckoutConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        checkout_token = serializer.validated_data["checkout_token"]

        event = BillingDemoEvent.objects.select_for_update().filter(checkout_token=checkout_token).first()
        if not event:
            raise ValidationError({"detail": "Checkout no encontrado."})

        if event.status == BillingDemoEvent.EventStatus.CONFIRMED:
            return Response({"detail": "Checkout ya confirmado.", "id_veterinaria": event.veterinaria_id}, status=status.HTTP_200_OK)

        if event.status in {
            BillingDemoEvent.EventStatus.CANCELLED,
            BillingDemoEvent.EventStatus.FAILED,
            BillingDemoEvent.EventStatus.EXPIRED,
        }:
            raise ValidationError({"detail": "Checkout no disponible para confirmar."})

        if event.expires_at < timezone.now():
            event.status = BillingDemoEvent.EventStatus.EXPIRED
            event.save(update_fields=["status", "updated_at"])
            raise ValidationError({"detail": "Checkout expirado."})

        paid = event.status == BillingDemoEvent.EventStatus.PAID
        if not paid and _stripe_enabled() and event.stripe_session_id:
            stripe.api_key = config("STRIPE_SECRET_KEY", default="")
            try:
                session = stripe.checkout.Session.retrieve(event.stripe_session_id)
                if getattr(session, "payment_status", None) == "paid":
                    _mark_event_as_paid(
                        event,
                        stripe_session_id=getattr(session, "id", None),
                        stripe_payment_intent_id=getattr(session, "payment_intent", None),
                        amount=getattr(session, "amount_total", None),
                        currency=getattr(session, "currency", None),
                    )
                    paid = True
            except Exception:
                paid = False

        if not paid and event.payment_mode == "DEMO" and event.status == BillingDemoEvent.EventStatus.STARTED:
            paid = True

        if not paid:
            raise ValidationError({"detail": "Pago no confirmado aÃºn."})

        data = event.payload
        role_admin = _get_role_or_raise("ADMIN")

        if Veterinaria.objects.filter(slug=(data.get("veterinaria_slug") or "").strip().lower()).exists():
            raise ValidationError({"veterinaria_slug": ["El slug ya estÃ¡ en uso."]})
        if User.objects.filter(correo=data.get("admin_correo")).exists():
            raise ValidationError({"admin_correo": ["El correo del administrador ya estÃ¡ registrado."]})

        veterinaria = Veterinaria.objects.create(
            nombre=(data.get("veterinaria_nombre") or "").strip(),
            slug=(data.get("veterinaria_slug") or "").strip().lower(),
            correo=(data.get("veterinaria_correo") or data.get("admin_correo") or "").strip(),
            telefono=(data.get("veterinaria_telefono") or data.get("admin_telefono") or "").strip(),
            direccion=(data.get("veterinaria_direccion") or "").strip(),
            estado=True,
        )

        admin_user = User.objects.create_user(
            correo=data.get("admin_correo"),
            password=data.get("admin_password"),
            role=role_admin,
            veterinaria=veterinaria,
            is_active=True,
        )
        Perfil.objects.create(
            usuario=admin_user,
            nombre=(data.get("admin_nombre") or "").strip(),
            telefono=(data.get("admin_telefono") or "").strip(),
            direccion=(data.get("admin_direccion") or "").strip(),
            estado=True,
        )

        veterinaria.owner_user = admin_user
        veterinaria.save(update_fields=["owner_user"])

        transaction.on_commit(
            lambda: threading.Thread(
                target=_seed_tenant_async,
                args=(veterinaria.id_veterinaria,),
                daemon=True,
            ).start()
        )

        fecha_inicio = timezone.localdate()
        _create_subscription(
            veterinaria=veterinaria,
            plan=event.plan,
            estado="ACTIVA",
            fecha_inicio=fecha_inicio,
            fecha_fin=None,
            renovacion_automatica=True,
        )

        event.status = BillingDemoEvent.EventStatus.CONFIRMED
        event.veterinaria = veterinaria
        event.user = admin_user
        event.confirmed_at = timezone.now()
        event.save(update_fields=["status", "veterinaria", "user", "confirmed_at", "updated_at"])

        tokens = get_tokens_for_user(admin_user)
        context = AuthContextService.get_auth_context(admin_user, "WEB")

        return Response(
            {
                "detail": "Compra confirmada y veterinaria activada.",
                "id_veterinaria": veterinaria.id_veterinaria,
                "owner_user_id": admin_user.id_usuario,
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "tokens": {"access": tokens["access"], "refresh": tokens["refresh"]},
                "user": context.get("usuario", {}),
                "context": context,
            },
            status=status.HTTP_200_OK,
        )

class DemoUpgradeStartView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_id = self.get_tenant_id()
        if not tenant_id:
            raise ValidationError({"detail": "No se pudo resolver la veterinaria actual."})

        serializer = DemoCheckoutStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        plan = PlanSuscripcion.objects.get(id_plan=data["plan_id"])
        checkout_token = secrets.token_urlsafe(32)

        event = BillingDemoEvent.objects.create(
            checkout_token=checkout_token,
            event_type=BillingDemoEvent.EventType.TRIAL_UPGRADE,
            status=BillingDemoEvent.EventStatus.STARTED,
            plan=plan,
            veterinaria_id=tenant_id,
            user=request.user,
            payload={},
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        return Response(
            {
                "checkout_token": checkout_token,
                "event_id": event.id_billing_demo_event,
                "expires_at": event.expires_at,
                "payment_mode": "DEMO",
                "detail": "Upgrade demo iniciado.",
            },
            status=status.HTTP_201_CREATED,
        )


class DemoUpgradeConfirmView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        tenant_id = self.get_tenant_id()
        if not tenant_id:
            raise ValidationError({"detail": "No se pudo resolver la veterinaria actual."})

        serializer = DemoCheckoutConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        checkout_token = serializer.validated_data["checkout_token"]

        event = BillingDemoEvent.objects.select_for_update().filter(
            checkout_token=checkout_token,
            event_type=BillingDemoEvent.EventType.TRIAL_UPGRADE,
            veterinaria_id=tenant_id,
        ).first()

        if not event:
            raise ValidationError({"detail": "Checkout de upgrade no encontrado."})

        if event.status == BillingDemoEvent.EventStatus.CONFIRMED:
            return Response({"detail": "Upgrade demo ya confirmado."}, status=status.HTTP_200_OK)

        if event.status != BillingDemoEvent.EventStatus.STARTED:
            raise ValidationError({"detail": "Checkout no disponible para confirmar."})

        if event.expires_at < timezone.now():
            event.status = BillingDemoEvent.EventStatus.CANCELLED
            event.save(update_fields=["status", "updated_at"])
            raise ValidationError({"detail": "Checkout demo expirado."})

        veterinaria = Veterinaria.objects.filter(id_veterinaria=tenant_id).first()
        if not veterinaria:
            raise ValidationError({"detail": "Veterinaria no encontrada."})

        fecha_inicio = timezone.localdate()
        _create_subscription(
            veterinaria=veterinaria,
            plan=event.plan,
            estado="ACTIVA",
            fecha_inicio=fecha_inicio,
            fecha_fin=None,
            renovacion_automatica=True,
        )

        event.status = BillingDemoEvent.EventStatus.CONFIRMED
        event.user = request.user
        event.confirmed_at = timezone.now()
        event.save(update_fields=["status", "user", "confirmed_at", "updated_at"])

        return Response(
            {"detail": "Upgrade demo confirmado. SuscripciÃƒÂ³n activa."},
            status=status.HTTP_200_OK,
        )



