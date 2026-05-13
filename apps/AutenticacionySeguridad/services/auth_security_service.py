import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError

from ..models import PasswordResetToken, User


LOCKOUT_MESSAGE = "Tu cuenta esta bloqueada temporalmente por intentos fallidos. Intenta nuevamente mas tarde."
GENERIC_LOGIN_MESSAGE = "Correo o contrasena incorrectos."


def get_lockout_config() -> tuple[int, int]:
    max_attempts = getattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 3)
    lock_minutes = getattr(settings, "LOGIN_LOCKOUT_MINUTES", 5)
    return max_attempts, lock_minutes


def get_password_reset_expiration_minutes() -> int:
    return getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES", 30)


def normalize_email(correo: str) -> str:
    return (correo or "").strip().lower()


def get_user_for_login(correo: str) -> User | None:
    correo_normalizado = normalize_email(correo)
    if not correo_normalizado:
        return None
    return (
        User.objects.select_related("role", "veterinaria")
        .filter(correo__iexact=correo_normalizado)
        .first()
    )


def clear_expired_lock(user: User) -> None:
    if user.bloqueado_hasta and user.bloqueado_hasta <= timezone.now():
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        user.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])


def ensure_user_not_blocked(user: User) -> None:
    clear_expired_lock(user)
    if user.bloqueado_hasta and user.bloqueado_hasta > timezone.now():
        retry_after_seconds = max(int((user.bloqueado_hasta - timezone.now()).total_seconds()), 0)
        raise PermissionDenied(
            detail={
                "detail": LOCKOUT_MESSAGE,
                "code": "CUENTA_BLOQUEADA",
                "bloqueado_hasta": user.bloqueado_hasta.isoformat(),
                "retry_after_seconds": retry_after_seconds,
            }
        )


@transaction.atomic
def register_failed_login(user_id: int) -> User:
    user = User.objects.select_for_update().get(pk=user_id)
    clear_expired_lock(user)

    max_attempts, lock_minutes = get_lockout_config()
    user.intentos_fallidos += 1

    if user.intentos_fallidos >= max_attempts:
        user.bloqueado_hasta = timezone.now() + timedelta(minutes=lock_minutes)

    user.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
    return user


@transaction.atomic
def register_successful_login(user_id: int) -> None:
    user = User.objects.select_for_update().get(pk=user_id)
    if user.intentos_fallidos != 0 or user.bloqueado_hasta is not None:
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        user.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])


def validate_login_password(user: User | None, raw_password: str) -> User:
    if not user or not user.check_password(raw_password):
        if user:
            user = register_failed_login(user.id_usuario)
            if user.bloqueado_hasta and user.bloqueado_hasta > timezone.now():
                ensure_user_not_blocked(user)
        raise AuthenticationFailed(
            detail={"detail": GENERIC_LOGIN_MESSAGE, "code": "LOGIN_FALLIDO"}
        )
    ensure_user_not_blocked(user)
    register_successful_login(user.id_usuario)
    user.refresh_from_db(fields=["intentos_fallidos", "bloqueado_hasta"])
    return user


@transaction.atomic
def invalidate_password_reset_tokens_for_user(user: User) -> None:
    PasswordResetToken.objects.select_for_update().filter(usuario=user, usado=False).update(usado=True)


@transaction.atomic
def create_password_reset_token(user: User) -> PasswordResetToken:
    invalidate_password_reset_tokens_for_user(user)
    token = secrets.token_urlsafe(32)
    expiration = timezone.now() + timedelta(minutes=get_password_reset_expiration_minutes())
    return PasswordResetToken.objects.create(
        usuario=user,
        token=token,
        expiracion=expiration,
    )


def build_password_reset_url(token: str) -> str:
    template = getattr(
        settings,
        "PASSWORD_RESET_URL_TEMPLATE",
        "{frontend_base_url}/reset-password?token={token}",
    )
    frontend_base_url = getattr(settings, "FRONTEND_BASE_URL", "http://127.0.0.1:3000")
    return template.format(token=token, frontend_base_url=frontend_base_url.rstrip("/"))


def send_password_reset_email(user: User, token: PasswordResetToken) -> None:
    reset_url = build_password_reset_url(token.token)
    expiration_minutes = get_password_reset_expiration_minutes()
    subject = "Recuperacion de contrasena - PetHome"
    message = (
        f"Hola,\n\n"
        f"Recibimos una solicitud para restablecer tu contrasena.\n"
        f"Usa este enlace para continuar:\n{reset_url}\n\n"
        f"El enlace expira en {expiration_minutes} minutos.\n"
        f"Si no solicitaste este cambio, ignora este mensaje."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pethome.local"),
        recipient_list=[user.correo],
        fail_silently=False,
    )


def validate_new_password(user: User, nueva_password: str) -> None:
    if len(nueva_password or "") < 8:
        raise ValidationError({"nueva_password": ["La nueva contrasena debe tener al menos 8 caracteres."]})
    try:
        password_validation.validate_password(nueva_password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"nueva_password": list(exc.messages)}) from exc


@transaction.atomic
def consume_password_reset_token(raw_token: str) -> PasswordResetToken:
    token = (
        PasswordResetToken.objects.select_for_update()
        .select_related("usuario")
        .filter(token=raw_token)
        .first()
    )
    if not token:
        raise ValidationError({"token": ["El token no es valido."]})
    if token.usado:
        raise ValidationError({"token": ["El token ya fue utilizado."]})
    if token.expiracion <= timezone.now():
        raise ValidationError({"token": ["El token ha expirado."]})
    return token


@transaction.atomic
def reset_user_password(token: PasswordResetToken, nueva_password: str) -> None:
    user = token.usuario
    validate_new_password(user, nueva_password)
    user.set_password(nueva_password)
    user.intentos_fallidos = 0
    user.bloqueado_hasta = None
    user.save(update_fields=["password", "intentos_fallidos", "bloqueado_hasta"])
    PasswordResetToken.objects.select_for_update().filter(usuario=user, usado=False).update(usado=True)


@transaction.atomic
def change_user_password(user: User, password_actual: str, nueva_password: str) -> None:
    if not user.check_password(password_actual):
        raise AuthenticationFailed(
            detail={"detail": "La contrasena actual es incorrecta.", "code": "PASSWORD_ACTUAL_INVALIDA"}
        )
    validate_new_password(user, nueva_password)
    user.set_password(nueva_password)
    user.intentos_fallidos = 0
    user.bloqueado_hasta = None
    user.save(update_fields=["password", "intentos_fallidos", "bloqueado_hasta"])
    PasswordResetToken.objects.select_for_update().filter(usuario=user, usado=False).update(usado=True)
