import ipaddress
import json
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.http import HttpRequest

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    UserType = AbstractBaseUser
else:
    UserType = Any

from ..events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
    construir_descripcion_evento,
)
from ..models.bitacora import Bitacora

logger = logging.getLogger(__name__)
User = get_user_model()


class BitacoraService:
    _SENSITIVE_METADATA_KEYS = {
        "password",
        "pass",
        "pwd",
        "token",
        "access",
        "refresh",
        "authorization",
        "secret",
    }

    @staticmethod
    def _normalizar_ip(ip: Optional[str]) -> Optional[str]:
        if not ip:
            return None

        ip_limpia = ip.strip()
        if not ip_limpia:
            return None

        try:
            return str(ipaddress.ip_address(ip_limpia))
        except ValueError:
            return None

    @staticmethod
    def _recortar_texto(value: Optional[str], max_length: int) -> str:
        if not value:
            return ""
        return str(value)[:max_length]

    @staticmethod
    def _sanitizar_valor_metadato(value: Any, key: Optional[str] = None) -> Any:
        if key and key.lower() in BitacoraService._SENSITIVE_METADATA_KEYS:
            return "***"

        if isinstance(value, dict):
            salida: Dict[str, Any] = {}
            for sub_key, sub_value in value.items():
                sub_key_str = str(sub_key)
                salida[sub_key_str] = BitacoraService._sanitizar_valor_metadato(
                    sub_value,
                    key=sub_key_str,
                )
            return salida

        if isinstance(value, (list, tuple, set)):
            return [BitacoraService._sanitizar_valor_metadato(item) for item in value]

        return value

    @staticmethod
    def _sanitizar_metadatos(metadatos: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not metadatos:
            return {}

        salida = BitacoraService._sanitizar_valor_metadato(metadatos)
        if not isinstance(salida, dict):
            return {}

        # Garantiza que el payload sea serializable a JSON para evitar fallos en DB.
        return json.loads(json.dumps(salida, default=str))

    @staticmethod
    def _resolver_usuario_actor(
        request: Optional[HttpRequest],
        usuario: Optional[UserType],
    ) -> Optional[UserType]:
        if usuario is not None:
            return usuario

        if (
            request is not None
            and hasattr(request, "user")
            and getattr(request.user, "is_authenticated", False)
        ):
            return request.user

        return None

    @staticmethod
    def obtener_ip(request: Optional[HttpRequest]) -> Optional[str]:
        if not request:
            return None

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_forwarded = x_forwarded_for.split(",")[0].strip()
            ip_normalizada = BitacoraService._normalizar_ip(ip_forwarded)
            if ip_normalizada:
                return ip_normalizada

        return BitacoraService._normalizar_ip(request.META.get("REMOTE_ADDR"))

    @staticmethod
    def obtener_user_agent(request: Optional[HttpRequest]) -> str:
        if not request:
            return ""
        return BitacoraService._recortar_texto(request.META.get("HTTP_USER_AGENT", ""), 1024)

    @staticmethod
    def registrar_evento(
        *,
        accion: str,
        descripcion: str = "",
        usuario: Optional[UserType] = None,
        request: Optional[HttpRequest] = None,
        modulo: str = BitacoraModulo.SISTEMA,
        entidad_tipo: str = "",
        entidad_id: str = "",
        resultado: str = BitacoraResultado.EXITO,
        metadatos: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
        user_agent: str = "",
    ) -> Optional[Bitacora]:
        """
        Registra un evento en la bitácora.
        Puede recibir request para extraer ip y user_agent automáticamente.
        """

        acciones_validas = {choice for choice, _ in BitacoraAccion.choices}
        modulos_validos = {choice for choice, _ in BitacoraModulo.choices}
        resultados_validos = {choice for choice, _ in BitacoraResultado.choices}

        if accion not in acciones_validas:
            logger.warning("Accion de bitacora invalida recibida: %s", accion)
            return None

        if modulo not in modulos_validos:
            logger.warning("Modulo de bitacora invalido recibido: %s", modulo)
            modulo = BitacoraModulo.SISTEMA

        if resultado not in resultados_validos:
            logger.warning("Resultado de bitacora invalido recibido: %s", resultado)
            resultado = BitacoraResultado.FALLO

        usuario = BitacoraService._resolver_usuario_actor(request=request, usuario=usuario)

        if request is not None:
            if not ip:
                ip = BitacoraService.obtener_ip(request)
            if not user_agent:
                user_agent = BitacoraService.obtener_user_agent(request)

        ip = BitacoraService._normalizar_ip(ip)
        user_agent = BitacoraService._recortar_texto(user_agent, 1024)
        entidad_tipo = BitacoraService._recortar_texto(entidad_tipo, 100)
        entidad_id = BitacoraService._recortar_texto(str(entidad_id) if entidad_id else "", 50)
        metadatos = BitacoraService._sanitizar_metadatos(metadatos)

        if not descripcion:
            actor = "Sistema/Anónimo"
            if usuario is not None:
                actor = getattr(usuario, "correo", None) or str(usuario)

            entidad = entidad_tipo or "registro"
            entidad_identificador = entidad_id or "N/A"

            descripcion = construir_descripcion_evento(
                accion,
                actor=actor,
                correo=metadatos.get("correo", ""),
                detalle=metadatos.get("detalle", ""),
                entidad=entidad,
                entidad_id=entidad_identificador,
            )

        try:
            return Bitacora.objects.create(
                usuario=usuario,
                accion=accion,
                descripcion=descripcion,
                ip=ip,
                user_agent=user_agent,
                modulo=modulo,
                entidad_tipo=entidad_tipo,
                entidad_id=entidad_id,
                resultado=resultado,
                metadatos=metadatos,
            )
        except Exception:
            logger.exception("No se pudo registrar evento en bitacora")
            return None

    @staticmethod
    def registrar_login_exitoso(request: HttpRequest, usuario: UserType) -> Optional[Bitacora]:
        return BitacoraService.registrar_evento(
            accion=BitacoraAccion.LOGIN,
            descripcion="Inicio de sesión exitoso.",
            usuario=usuario,
            request=request,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
        )

    @staticmethod
    def registrar_login_fallido(
        request: Optional[HttpRequest],
        identificador: str = ""
    ) -> Optional[Bitacora]:
        identificador_limpio = BitacoraService._recortar_texto(identificador, 200)
        return BitacoraService.registrar_evento(
            accion=BitacoraAccion.LOGIN_FALLIDO,
            descripcion=f"Intento de inicio de sesión fallido. Identificador: {identificador_limpio}".strip(),
            request=request,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.FALLO,
            metadatos={"identificador": identificador_limpio},
        )

    @staticmethod
    def registrar_logout(request: HttpRequest, usuario: UserType) -> Optional[Bitacora]:
        return BitacoraService.registrar_evento(
            accion=BitacoraAccion.LOGOUT,
            descripcion="Cierre de sesión exitoso.",
            usuario=usuario,
            request=request,
            modulo=BitacoraModulo.AUTENTICACION,
            resultado=BitacoraResultado.EXITO,
        )

    @staticmethod
    def registrar_acceso_denegado(
        request: Optional[HttpRequest],
        descripcion: str = "Intento de acceso denegado.",
        usuario: Optional[UserType] = None,
        modulo: str = BitacoraModulo.SISTEMA,
        metadatos: Optional[Dict[str, Any]] = None,
    ) -> Optional[Bitacora]:
        return BitacoraService.registrar_evento(
            accion=BitacoraAccion.ACCESO_DENEGADO,
            descripcion=descripcion,
            usuario=usuario,
            request=request,
            modulo=modulo,
            resultado=BitacoraResultado.FALLO,
            metadatos=metadatos,
        )