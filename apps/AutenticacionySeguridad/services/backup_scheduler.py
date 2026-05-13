import logging
from datetime import datetime, timedelta
from typing import Optional

from django.utils import timezone
from django.contrib.auth import get_user_model

from ..models.backup_config import BackupConfig
from ..models.veterinaria import Veterinaria
from ..models.backup_restore import BackupRestore
from .backup_service import BackupService
from .bitacora_register_service import BitacoraService

logger = logging.getLogger(__name__)

User = get_user_model()


class BackupScheduler:
    """
    Scheduler para ejecutar backups automáticos según la configuración de cada veterinaria.
    Debe ser llamado periódicamente (ej: cada hora o cada 30 minutos) por un cron o task queue.
    """

    @staticmethod
    def run_scheduled_backups() -> dict:
        """
        Verifica todas las configuraciones de backup y ejecuta las que estén vencidas.
        Considera frecuencia, hora_ejecucion, y dias_semana para PERSONALIZADO.
        Retorna un resumen de operaciones realizadas.
        """
        logger.info("Iniciando ejecución de backups programados...")
        
        summary = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        try:
            now = timezone.now()
            
            # Obtener todas las configuraciones activas
            configs = BackupConfig.objects.filter(
                activo=True,
            ).select_related("veterinaria")
            
            logger.info(f"Verificando {configs.count()} configuraciones de backup activas")
            
            for config in configs:
                try:
                    # Verificar si es tiempo de ejecutar este backup
                    if not BackupScheduler._should_run_backup(config, now):
                        summary["skipped"] += 1
                        continue
                    
                    summary["total_processed"] += 1
                    
                    # Ejecutar backup automático
                    backup = BackupScheduler._execute_scheduled_backup(config)
                    
                    if backup and backup.estado == "EXITOSO":
                        summary["successful"] += 1
                        logger.info(f"Backup automático exitoso para veterinaria {config.veterinaria.id_veterinaria}")
                    else:
                        summary["failed"] += 1
                        logger.warning(f"Backup automático fallido para veterinaria {config.veterinaria.id_veterinaria}")
                        summary["errors"].append({
                            "veterinaria_id": config.veterinaria.id_veterinaria,
                            "reason": "Backup retornó null o estado diferente a EXITOSO"
                        })
                    
                    # Solo avanzar la programación cuando el backup fue exitoso.
                    # Si falla, dejamos la fecha vencida para reintentar en el siguiente ciclo.
                    if backup and backup.estado == "EXITOSO":
                        BackupScheduler._update_next_backup_time(
                            config,
                            reference_time=backup.fecha_hora,
                        )
                    
                    # Limpiar backups antiguos según política de retención
                    BackupService.cleanup_old_backups(
                        config.veterinaria.id_veterinaria,
                        config.dias_retención
                    )
                    
                except Exception as e:
                    summary["failed"] += 1
                    error_msg = f"Error procesando backup para veterinaria {config.veterinaria.id_veterinaria}: {str(e)}"
                    logger.exception(error_msg)
                    summary["errors"].append({
                        "veterinaria_id": config.veterinaria.id_veterinaria,
                        "reason": str(e)
                    })
            
            logger.info(f"Ejecución de backups completada: {summary}")
            return summary
            
        except Exception as e:
            logger.exception(f"Error fatal en run_scheduled_backups: {str(e)}")
            summary["errors"].append({
                "global_error": str(e)
            })
            return summary

    @staticmethod
    def _should_run_backup(config: BackupConfig, now: datetime) -> bool:
        """
        Determina si es tiempo de ejecutar el backup para esta configuración.
        
        Considera:
        - Si próximo_backup_programado ya pasó
        - Que no se ejecute más de una vez por día para la misma config
        - Que respete la hora_ejecucion para frecuencias personalizadas
        
        Args:
            config: BackupConfig a verificar
            now: datetime actual
            
        Returns:
            True si debe ejecutarse, False en caso contrario
        """
        if not config.próximo_backup_programado:
            logger.warning(
                f"BackupConfig {config.id_backup_config} sin próximo_backup_programado; inicializando"
            )
            try:
                config.próximo_backup_programado = BackupService._calculate_next_backup_with_config(config)
                config.save(update_fields=["próximo_backup_programado", "actualizado"])
                logger.info(
                    f"BackupConfig {config.id_backup_config} inicializado para {config.próximo_backup_programado}"
                )
            except Exception as e:
                logger.error(
                    f"No se pudo inicializar próximo_backup_programado para BackupConfig {config.id_backup_config}: {str(e)}"
                )
            return False
        
        # Verificar si el tiempo programado ya pasó
        if config.próximo_backup_programado > now:
            return False
        
        # Verificar si hay un backup reciente (últimos 30 minutos) para evitar duplicados
        thirty_minutes_ago = now - timedelta(minutes=30)
        recent_backup = BackupRestore.objects.filter(
            veterinaria=config.veterinaria,
            tipo="BACKUP",
            estado="EXITOSO",
            fecha_hora__gte=thirty_minutes_ago
        ).order_by("-fecha_hora").first()
        
        if recent_backup:
            logger.info(
                f"Backup reciente encontrado para veterinaria {config.veterinaria.id_veterinaria}, "
                f"saltando ejecución"
            )
            BackupScheduler._update_next_backup_time(
                config,
                reference_time=recent_backup.fecha_hora,
            )
            return False
        
        return True

    @staticmethod
    def _execute_scheduled_backup(config: BackupConfig):
        """
        Ejecuta un backup automático para una configuración específica.
        """
        try:
            # Preferir un usuario administrador de la misma veterinaria.
            # El superadmin queda como respaldo solo si no existe un admin activo del tenant.
            admin_user = User.objects.filter(
                veterinaria_id=config.veterinaria.id_veterinaria,
                is_active=True,
                is_staff=True,
                is_superuser=False,
            ).order_by("-date_joined").first()
            if not admin_user:
                admin_user = User.objects.filter(
                    veterinaria_id=config.veterinaria.id_veterinaria,
                    is_active=True,
                    role__nombre__in=["ADMIN", "SUPERADMIN"],
                ).order_by("-date_joined").first()
            if not admin_user:
                admin_user = User.objects.filter(is_superuser=True, is_active=True).first()
            if not admin_user:
                raise Exception("No se encontró usuario administrador ni superadmin para registrar backup automático")
            
            motivo = f"Backup automático - Frecuencia: {config.frecuencia}"

            backup = BackupService.create_backup(
                veterinaria_id=config.veterinaria.id_veterinaria,
                usuario=admin_user,
                request=None,  # Sin request HTTP
                motivo=motivo,
                es_automatico=True,
            )
            
            return backup
            
        except Exception as e:
            logger.error(f"Error ejecutando backup automático: {str(e)}")
            return None

    @staticmethod
    def _update_next_backup_time(
        config: BackupConfig,
        reference_time: Optional[datetime] = None,
    ) -> None:
        """
        Actualiza la fecha/hora del próximo backup según la frecuencia y configuración personalizada.
        """
        try:
            next_backup_time = BackupService._calculate_next_backup_with_config(
                config,
                reference_time=reference_time,
            )
            config.próximo_backup_programado = next_backup_time
            # Guardar solo el campo programado evita sobreescribir `último_backup`
            # con valores stale de la instancia en memoria.
            config.save(update_fields=["próximo_backup_programado", "actualizado"])
            
            logger.info(
                f"Próximo backup para veterinaria {config.veterinaria.id_veterinaria} "
                f"programado para: {next_backup_time}"
            )
        except Exception as e:
            logger.error(f"Error actualizando próximo backup: {str(e)}")

    @staticmethod
    def check_and_create_default_configs() -> int:
        """
        Crea configuraciones de backup por defecto para veterinarias que no las tengan.
        Retorna la cantidad de configuraciones creadas.
        """
        try:
            created_count = 0
            
            # Obtener todas las veterinarias
            veterinarias = Veterinaria.objects.all()
            
            for veterinaria in veterinarias:
                config, created = BackupConfig.objects.get_or_create(
                    veterinaria_id=veterinaria.id_veterinaria,
                    defaults={
                        "frecuencia": "SEMANAL",
                        "dias_retención": 30,
                        "activo": True,
                    }
                )
                
                if created:
                    created_count += 1
                    logger.info(f"Configuración de backup creada para veterinaria {veterinaria.id_veterinaria}")
            
            logger.info(f"Total de configuraciones de backup creadas: {created_count}")
            return created_count
            
        except Exception as e:
            logger.error(f"Error creando configuraciones por defecto: {str(e)}")
            return 0
