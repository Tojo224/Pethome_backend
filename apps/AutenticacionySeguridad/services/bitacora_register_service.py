import logging
from typing import Any, Dict, Optional

from django.http import HttpRequest

from ..models.bitacora import Bitacora

logger = logging.getLogger(__name__)


class BitacoraService:
    @staticmethod
    def registrar_evento(
        *,
        accion: str,
        descripcion: str = "",
        usuario: Optional[Any] = None,
        request: Optional[HttpRequest] = None,
        modulo: str = "",
        entidad_tipo: str = "",
        entidad_id: str = "",
        resultado: str = "",
        metadatos: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
        user_agent: str = "",
    ) -> Optional[Bitacora]:
        try:
            if request is not None:
                forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
                ip = ip or (forwarded_for.split(",")[0].strip() if forwarded_for else "")
                ip = ip or request.META.get("REMOTE_ADDR", "")
                user_agent = user_agent or request.META.get("HTTP_USER_AGENT", "")

            veterinaria_id = None
            usuario_id = None
            nombre_usuario = ""
            correo_usuario = ""
            if usuario is not None:
                usuario_id = getattr(usuario, "id_usuario", None)
                correo_usuario = getattr(usuario, "correo", "")
                
                # Intentar obtener el nombre del perfil, usar correo como respaldo
                try:
                    perfil = getattr(usuario, "perfil", None)
                    nombre_usuario = getattr(perfil, "nombre", "") if perfil else ""
                except Exception:
                    nombre_usuario = ""
                
                if not nombre_usuario:
                    nombre_usuario = correo_usuario or f"Usuario {usuario_id}"

                if getattr(usuario, "is_superuser", False):
                    veterinaria_id = None
                else:
                    veterinaria_id = getattr(usuario, "veterinaria_id", None)

            if request is not None and not getattr(usuario, "is_superuser", False):
                tenant = getattr(request, "tenant", None)
                tenant_id = getattr(tenant, "id", None)
                if tenant_id:
                    veterinaria_id = tenant_id

            payload = {
                "id_usuario": usuario_id,
                "nombre_usuario": nombre_usuario,
                "correo_usuario": correo_usuario,
                "accion": accion,
                "descripcion": descripcion,
                "modulo": modulo,
                "entidad_tipo": entidad_tipo,
                "entidad_id": str(entidad_id) if entidad_id is not None else "",
                "resultado": resultado,
                "metadatos": metadatos or {},
                "ip": ip or "",
                "user_agent": user_agent or "",
                "usuario_id": usuario_id,
                "path": getattr(request, "path", "") if request else "",
                "method": getattr(request, "method", "") if request else "",
            }

            return Bitacora.objects.create(
                veterinaria_id=veterinaria_id,
                payload=payload,
            )
        except Exception:
            logger.exception("No se pudo registrar evento en bitacora")
            return None

    @staticmethod
    def registrar_login_exitoso(request: HttpRequest, usuario: Any) -> Optional[Bitacora]:
        return BitacoraService.registrar_evento(
            accion="LOGIN",
            descripcion="Inicio de sesión exitoso.",
            usuario=usuario,
            request=request,
            modulo="autenticacion",
            resultado="EXITO",
        )

    @staticmethod
    def registrar_login_fallido(request: Optional[HttpRequest], identificador: str = "") -> Optional[Bitacora]:
        return BitacoraService.registrar_evento(
            accion="LOGIN_FALLIDO",
            descripcion=f"Intento de inicio de sesión fallido. Identificador: {identificador}",
            request=request,
            modulo="autenticacion",
            resultado="FALLO",
            metadatos={"identificador": identificador},
        )

    @staticmethod
    def registrar_logout(request: HttpRequest, usuario: Any) -> Optional[Bitacora]:
        return BitacoraService.registrar_evento(
            accion="LOGOUT",
            descripcion="Cierre de sesión exitoso.",
            usuario=usuario,
            request=request,
            modulo="autenticacion",
            resultado="EXITO",
        )

    @staticmethod
    def registrar_acceso_denegado(
        request: Optional[HttpRequest],
        descripcion: str = "Intento de acceso denegado.",
        usuario: Optional[Any] = None,
        modulo: str = "sistema",
        metadatos: Optional[Dict[str, Any]] = None,
    ) -> Optional[Bitacora]:
        return BitacoraService.registrar_evento(
            accion="ACCESO_DENEGADO",
            descripcion=descripcion,
            usuario=usuario,
            request=request,
            modulo=modulo,
            resultado="FALLO",
            metadatos=metadatos,
        )
