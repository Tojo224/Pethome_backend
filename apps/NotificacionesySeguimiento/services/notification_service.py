import logging
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from apps.NotificacionesySeguimiento.models import Notificacion, DispositivoUsuario, ConfiguracionNotificacion
from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService
from firebase_admin import messaging

logger = logging.getLogger(__name__)

class NotificationService:
    @classmethod
    def _is_duplicate(cls, user_id, title, message):
        """Evita enviar la misma notificación al mismo usuario dos veces en un periodo corto (2 segundos)"""
        hash_key = hashlib.md5(f"notif_{user_id}_{title}_{message}".encode()).hexdigest()
        if cache.get(hash_key):
            return True
        cache.set(hash_key, True, 2) # Bloquear por 2 segundos
        return False

    @staticmethod
    def crear_notificacion(
        usuario, 
        titulo: str, 
        mensaje: str, 
        tipo: str, 
        id_entidad: Optional[int] = None
    ) -> Notificacion:
        """
        Crea un registro de notificación en la base de datos.
        """
        notificacion = Notificacion.objects.create(
            usuario=usuario,
            veterinaria=usuario.veterinaria,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            id_entidad_relacionada=id_entidad
        )
        return notificacion

    @staticmethod
    def enviar_notificacion_push(notificacion: Notificacion) -> bool:
        """
        Envía la notificación a todos los dispositivos activos del usuario usando FCM.
        """
        dispositivos = DispositivoUsuario.objects.filter(
            usuario=notificacion.usuario, 
            activo=True
        )
        
        if not dispositivos.exists():
            logger.info(f"No hay dispositivos activos para el usuario {notificacion.usuario.correo}")
            return False

        tokens = [d.token_fcm for d in dispositivos]
        
        try:
            # Construir el mensaje para FCM
            mensaje_fcm = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=notificacion.titulo,
                    body=notificacion.mensaje,
                ),
                data={
                    "id_notificacion": str(notificacion.id_notificacion),
                    "tipo": notificacion.tipo,
                    "id_entidad": str(notificacion.id_entidad_relacionada) if notificacion.id_entidad_relacionada else "",
                    "link": notificacion.link or ""
                },
                tokens=tokens,
            )

            # Enviar vía Firebase
            response = messaging.send_each_for_multicast(mensaje_fcm)
            
            # Manejar tokens inválidos (limpieza automática)
            if response.failure_count > 0:
                for idx, res in enumerate(response.responses):
                    if not res.success:
                        token_erroneo = tokens[idx]
                        error_code = getattr(res.exception, 'code', 'unknown')
                        
                        # Solo desactivamos si el error indica que el token ya no es válido
                        # Códigos comunes: 'registration-token-not-registered', 'invalid-argument'
                        if error_code in ['registration-token-not-registered', 'invalid-argument']:
                            logger.warning(f"Token inválido detectado ({error_code}): {token_erroneo[:10]}... desactivando.")
                            DispositivoUsuario.objects.filter(token_fcm=token_erroneo).update(activo=False)
                        else:
                            logger.error(f"Error al enviar a token {token_erroneo[:10]}...: {error_code}")

            # Actualizar estado de la notificación local
            notificacion.estado = Notificacion.EstadoNotificacion.ENVIADA
            notificacion.fecha_envio = timezone.now()
            notificacion.save()

            # Registrar en Bitácora
            BitacoraService.registrar_evento(
                accion="NOTIFICACION_ENVIADA",
                descripcion=f"Notificación '{notificacion.titulo}' enviada. Éxitos: {response.success_count}, Fallos: {response.failure_count}",
                usuario=notificacion.usuario,
                modulo="Notificaciones",
                resultado="EXITO",
                metadatos={
                    "id_notificacion": notificacion.id_notificacion, 
                    "tokens_intentados": len(tokens),
                    "exitos": response.success_count,
                    "fallos": response.failure_count
                }
            )
            return response.success_count > 0
        except Exception as e:
            logger.error(f"Error crítico al enviar notificación push: {str(e)}")
            notificacion.estado = Notificacion.EstadoNotificacion.FALLIDA
            notificacion.save()
            
            BitacoraService.registrar_evento(
                accion="NOTIFICACION_FALLIDA",
                descripcion=f"Fallo al enviar notificación push: {str(e)}",
                usuario=notificacion.usuario,
                modulo="Notificaciones",
                resultado="FALLO",
                metadatos={"id_notificacion": notificacion.id_notificacion}
            )
            return False

    @classmethod
    def notify_user(cls, user, title: str, message: str, tipo: str = 'AVISO', id_entidad: Optional[int] = None, link: Optional[str] = None):
        """
        Método unificado para enviar notificaciones a un usuario.
        """
        # Evitar duplicados accidentales
        if cls._is_duplicate(user.pk, title, message):
            return None

        # 1. Crear registro
        notificacion = cls.crear_notificacion(user, title, message, tipo, id_entidad)
        
        # Guardar link si existe
        if link:
            notificacion.link = link
            notificacion.save()

        # 2. Enviar push
        return cls.enviar_notificacion_push(notificacion)

    @classmethod
    def notify_veterinaria(cls, veterinaria, title: str, message: str, tipo: str = 'AVISO', id_entidad: Optional[int] = None, link: Optional[str] = None):
        """
        Envía una notificación a todos los empleados (Admin/Staff) de una veterinaria de forma eficiente.
        """
        from apps.AutenticacionySeguridad.models import User
        
        # 1. Obtener todos los IDs de usuario del staff
        staff_users = User.objects.filter(veterinaria=veterinaria).exclude(role__nombre='CLIENT')
        
        if not staff_users.exists():
            return False

        # 2. Crear registros individuales en la BD para el historial de cada uno
        # (Esto es rápido porque es base de datos local)
        for member in staff_users:
            cls.crear_notificacion(member, title, message, tipo, id_entidad)
            # Nota: No actualizamos el link individualmente aquí para ir rápido, 
            # pero el push lo llevará.

        # 3. Obtener TODOS los tokens activos de todo el staff
        dispositivos = DispositivoUsuario.objects.filter(
            usuario__in=staff_users,
            activo=True
        )
        
        if not dispositivos.exists():
            return False

        tokens = [d.token_fcm for d in dispositivos]

        # 4. Enviar un ÚNICO mensaje multicast a todos
        try:
            mensaje_fcm = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=message),
                data={
                    "tipo": tipo,
                    "id_entidad": str(id_entidad) if id_entidad else "",
                    "link": link or ""
                },
                tokens=tokens,
            )
            messaging.send_each_for_multicast(mensaje_fcm)
            return True
        except Exception as e:
            logger.error(f"Error en envío masivo a veterinaria: {e}")
            return False
