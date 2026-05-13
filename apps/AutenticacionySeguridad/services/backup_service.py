import logging
import os
import json
import re
import subprocess
import hashlib
import zipfile
import tempfile
import mimetypes
from collections import deque
from glob import glob
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional, Dict, Any
from io import BytesIO
from shutil import which
from pathlib import Path
import time

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.management.color import no_style
from django.db import connection, models, transaction, IntegrityError
from django.utils import timezone

from ..models.backup_restore import BackupRestore
from ..models.backup_config import BackupConfig
from ..models.veterinaria import Veterinaria
from .bitacora_register_service import BitacoraService

logger = logging.getLogger(__name__)


class BackupService:
    """
    Servicio para gestionar backups y restauraciones de PostgreSQL.
    Encapsula lógica de pg_dump, GCS y auditoría.
    """

    @staticmethod
    def create_backup(
        veterinaria_id: int,
        usuario: Any,
        request: Optional[Any] = None,
        motivo: str = "Backup manual",
        scope: str = "TENANT",
        es_automatico: bool = False,
    ) -> Optional[BackupRestore]:
        """
        Crea un backup manual de la BD para una veterinaria específica.
        Genera archivo SQL, sube a GCS y registra en BackupRestore y BitácoraService.
        """
        try:
            # Soporte para backups GLOBAL o por veterinaria
            scope = str(scope or "TENANT").upper()
            if scope not in {"TENANT", "GLOBAL"}:
                scope = "TENANT"

            motivo = (motivo or "").strip()
            if es_automatico:
                if motivo:
                    if not motivo.lower().startswith("backup automático"):
                        motivo = f"Backup automático - {motivo}"
                else:
                    motivo = "Backup automático"
            elif not motivo:
                motivo = "Backup manual"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if scope == "GLOBAL" and getattr(usuario, "is_superuser", False):
                # Crear registro global (asociar a superadmin sin veterinaria específica)
                # Asociamos a la primera veterinaria como referencia para la FK (modelo requiere FK)
                first_vet = Veterinaria.objects.order_by("id_veterinaria").first()
                if not first_vet:
                    raise Exception("No hay veterinarias para crear backup global")

                backup_record = BackupRestore.objects.create(
                    tipo="BACKUP",
                    estado="INICIADO",
                    usuario=usuario,
                    veterinaria=first_vet,
                    motivo=motivo,
                    proveedor_almacenamiento="GCS",
                )

                try:
                    # Dump SQL completo de toda la base de datos
                    global_sql = BackupService._generate_pg_dump(None)
                    filename = f"backup_global_{timestamp}.sql"
                    
                    # Verificar salida del dump global
                    if global_sql is None or global_sql == "":
                        raise Exception("pg_dump global devolvió salida vacía o None")

                    # Calcular hash
                    try:
                        hash_archivo = hashlib.sha256(global_sql.encode()).hexdigest()
                    except Exception as e:
                        raise Exception(f"Error calculando hash del dump global: {str(e)}")
                    
                    # Subir a GCS
                    ruta_remota = BackupService._upload_to_gcs(
                        filename,
                        global_sql,
                        first_vet.id_veterinaria,
                        scope="GLOBAL",
                    )

                    # También subir MEDIA como blobs individuales a GCS
                    media_prefix = BackupService._media_backup_prefix_from_sql_blob_path(ruta_remota)
                    media_stats = BackupService._upload_media_files_to_gcs(media_prefix)
                    
                    # Actualizar registro de forma robusta (reintentos si la conexión falla)
                    BackupService._safe_update_backup_record(
                        backup_record,
                        {
                            "estado": "EXITOSO",
                            "ruta_archivo": ruta_remota,
                            "hash_archivo": hash_archivo,
                        },
                    )

                    # Registrar bitácora
                    vets = list(Veterinaria.objects.all())
                    BitacoraService.registrar_evento(
                        accion="BACKUP_GLOBAL_CREADO",
                        descripcion="Backup SQL global (todas las clínicas) creado exitosamente",
                        usuario=usuario,
                        request=request,
                        modulo="backups",
                        entidad_tipo="BackupRestore",
                        entidad_id=str(backup_record.id_backup_restore),
                        resultado="EXITO",
                        metadatos={
                            "ruta_gcs": ruta_remota,
                            "ruta_media_gcs": media_prefix,
                            "media_archivos_subidos": media_stats.get("files", 0),
                            "hash": hash_archivo,
                            "tamaño_bytes": len(global_sql),
                            "veterinarias_incluidas": [v.id_veterinaria for v in vets],
                        },
                    )

                    logger.info(f"Backup GLOBAL exitoso: {filename}")
                    # Actualizar BackupConfig de referencia para reflejar la última copia global
                    try:
                        backup_config, _ = BackupConfig.objects.get_or_create(
                            veterinaria_id=first_vet.id_veterinaria
                        )
                        backup_config.último_backup = timezone.now()
                        backup_config.save(update_fields=["último_backup", "actualizado"])
                    except Exception:
                        logger.exception("No se pudo actualizar BackupConfig.último_backup para GLOBAL")
                    return backup_record
                except Exception as e:
                    backup_record.estado = "FALLIDO"
                    backup_record.motivo = f"Error en backup global: {str(e)}"
                    backup_record.save()
                    BitacoraService.registrar_evento(
                        accion="BACKUP_GLOBAL_FALLIDO",
                        descripcion=f"Fallo backup global: {str(e)}",
                        usuario=usuario,
                        request=request,
                        modulo="backups",
                        resultado="FALLO",
                    )
                    logger.error(f"Backup GLOBAL fallido: {str(e)}")
                    return None

            # Default: backup por veterinaria (existing behavior)
            veterinaria = Veterinaria.objects.get(id_veterinaria=veterinaria_id)
            
            # Crear registro en estado INICIADO
            backup_record = BackupRestore.objects.create(
                tipo="BACKUP",
                estado="INICIADO",
                usuario=usuario,
                veterinaria=veterinaria,
                motivo=motivo,
                proveedor_almacenamiento="GCS",
            )

            # Generar nombre del archivo con timestamp
            filename = f"backup_{veterinaria.id_veterinaria}_{timestamp}.sql"
            
            # Realizar pg_dump
            try:
                dump_content = BackupService._generate_pg_dump(veterinaria_id)
                
                # Verificar que el dump se generó correctamente
                if dump_content is None or dump_content == "":
                    raise Exception("pg_dump devolvió salida vacía o None")

                # Calcular hash
                try:
                    hash_archivo = hashlib.sha256(dump_content.encode()).hexdigest()
                except Exception as e:
                    raise Exception(f"Error calculando hash del dump: {str(e)}")
                
                # Subir a GCS
                ruta_remota = BackupService._upload_to_gcs(
                    filename, dump_content, veterinaria_id
                )
                
                # Actualizar registro como exitoso
                # Actualizar registro de forma robusta (reintentos si la conexión falla)
                BackupService._safe_update_backup_record(
                    backup_record,
                    {
                        "estado": "EXITOSO",
                        "ruta_archivo": ruta_remota,
                        "hash_archivo": hash_archivo,
                    },
                )
                
                # Actualizar última copia en BackupConfig (usar timezone-aware)
                backup_config, _ = BackupConfig.objects.get_or_create(
                    veterinaria_id=veterinaria_id
                )
                backup_config.último_backup = timezone.now()
                if es_automatico:
                    backup_config.próximo_backup_programado = (
                        BackupService._calculate_next_backup_with_config(
                            backup_config,
                            reference_time=backup_config.último_backup,
                        )
                    )
                    backup_config.save(
                        update_fields=[
                            "último_backup",
                            "próximo_backup_programado",
                            "actualizado",
                        ]
                    )
                else:
                    backup_config.save(update_fields=["último_backup", "actualizado"])
                
                # Registrar en bitácora
                BitacoraService.registrar_evento(
                    accion="BACKUP_MANUAL_CREADO",
                    descripcion=f"Backup manual creado exitosamente para {veterinaria.nombre}",
                    usuario=usuario,
                    request=request,
                    modulo="backups",
                    entidad_tipo="BackupRestore",
                    entidad_id=str(backup_record.id_backup_restore),
                    resultado="EXITO",
                    metadatos={
                        "veterinaria_id": veterinaria_id,
                        "hash": hash_archivo,
                        "ruta_gcs": ruta_remota,
                        "tamaño_bytes": len(dump_content),
                    }
                )
                
                logger.info(f"Backup exitoso para veterinaria {veterinaria_id}: {filename}")
                return backup_record
                
            except Exception as e:
                backup_record.estado = "FALLIDO"
                backup_record.motivo = f"Error en generación o subida: {str(e)}"
                backup_record.save()
                
                BitacoraService.registrar_evento(
                    accion="BACKUP_MANUAL_FALLIDO",
                    descripcion=f"Fallo al crear backup manual: {str(e)}",
                    usuario=usuario,
                    request=request,
                    modulo="backups",
                    resultado="FALLO",
                    metadatos={
                        "veterinaria_id": veterinaria_id,
                        "error": str(e),
                    }
                )
                
                logger.error(f"Backup fallido para veterinaria {veterinaria_id}: {str(e)}")
                return None
                
        except Veterinaria.DoesNotExist:
            logger.error(f"Veterinaria {veterinaria_id} no encontrada")
            BitacoraService.registrar_evento(
                accion="BACKUP_ERROR",
                descripcion=f"Veterinaria no encontrada: {veterinaria_id}",
                usuario=usuario,
                request=request,
                modulo="backups",
                resultado="FALLO",
            )
            return None
        except Exception as e:
            logger.exception(f"Error inesperado en create_backup: {str(e)}")
            return None

    @staticmethod
    def _backup_restore_history(veterinaria_id: Optional[int] = None) -> list[Dict[str, Any]]:
        """
        Realiza un backup de los registros BackupRestore en memoria para preservarlos durante restore.
        Si veterinaria_id se proporciona, solo guarda los de esa vet.
        """
        try:
            if veterinaria_id:
                records = BackupRestore.objects.filter(veterinaria_id=veterinaria_id).values()
            else:
                records = BackupRestore.objects.values()
            
            # Convertir a list para poder almacenar en memoria
            history = list(records)
            logger.info(f"Backed up {len(history)} BackupRestore records to memory")
            return history
        except Exception as e:
            logger.error(f"Error backing up restore history: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def _restore_restore_history(history: list[Dict[str, Any]]) -> None:
        """
        Re-inserta los registros BackupRestore que se perdieron durante la restauración BD.
        """
        if not history:
            return
        
        try:
            restored_count = 0
            updated_count = 0
            for record_data in history:
                try:
                    # Ignorar el id automático, Django lo recreará
                    record_data_clean = {k: v for k, v in record_data.items() if k != 'id_backup_restore'}
                    
                    # Si ya existe tras restore desde dump, lo actualizamos con el estado
                    # pre-restore para preservar EXITOSO/FALLIDO originales.
                    if 'id_backup_restore' in record_data and record_data['id_backup_restore']:
                        existing_qs = BackupRestore.objects.filter(id_backup_restore=record_data['id_backup_restore'])
                        if existing_qs.exists():
                            existing = existing_qs.first()
                            # Regla anti-regresión: nunca degradar EXITOSO a INICIADO.
                            incoming_estado = record_data_clean.get("estado")
                            if existing and existing.estado == "EXITOSO" and incoming_estado == "INICIADO":
                                record_data_clean["estado"] = "EXITOSO"
                            existing_qs.update(**record_data_clean)
                            updated_count += 1
                            continue
                    
                    # Recrear el registro
                    BackupRestore.objects.create(**record_data_clean)
                    restored_count += 1
                except Exception as e:
                    logger.warning(f"Error restoring individual record: {str(e)}")
                    continue
            
            logger.info(
                "Restored %s and updated %s of %s BackupRestore records from memory",
                restored_count,
                updated_count,
                len(history),
            )
        except Exception as e:
            logger.error(f"Error restoring history: {str(e)}", exc_info=True)

    @staticmethod
    def _wait_for_table(table_name: str, timeout_seconds: int = 60, poll_interval: float = 1.0) -> bool:
        """
        Espera hasta que la tabla indicada exista en la base de datos o hasta expirar el timeout.
        Usa `to_regclass` para comprobar existencia de tabla en PostgreSQL y reintenta cerrando
        la conexión entre intentos para forzar reinstanciación de la sesión DB.
        """
        import time
        from django.db import connection

        deadline = time.time() + float(timeout_seconds)
        while time.time() < deadline:
            try:
                # Cerrar la conexión anterior por si psql invalidó la sesión
                connection.close()
                with connection.cursor() as cur:
                    cur.execute("SELECT to_regclass(%s)", [table_name])
                    exists = cur.fetchone()[0]
                    if exists:
                        return True
            except Exception:
                logger.debug(f"Comprobación de tabla {table_name} falló; reintentando")
            time.sleep(poll_interval)

        logger.error(f"Timeout esperando la tabla {table_name} después de {timeout_seconds}s")
        return False

    @staticmethod
    def restore_backup(
        backup_id: int,
        usuario: Any,
        request: Optional[Any] = None,
        motivo: str = "Restauración manual",
        scope: str = "TENANT",
        veterinaria_id_target: Optional[int] = None,
    ) -> bool:
        """
        Restaura una BD desde un backup seleccionado.
        Descarga de GCS, inyecta en BD y registra resultado.
        
        Args:
            backup_id: ID del backup a restaurar
            usuario: Usuario que ejecuta la restauración
            request: Request object para bitácora
            motivo: Razón de la restauración
            scope: "TENANT" (solo esa vet) o "GLOBAL" (toda la BD)
            veterinaria_id_target: Si está set y backup es GLOBAL, restaura solo esa vet
        """
        try:
            backup = BackupRestore.objects.get(id_backup_restore=backup_id, tipo="BACKUP")

            scope = (scope or "TENANT").upper()
            
            # Backup del historial ANTES de restaurar (se perderá durante el psql)
            restore_history = BackupService._backup_restore_history(
                veterinaria_id=backup.veterinaria.id_veterinaria if scope == "TENANT" else None
            )
            
            # Crear registro de restauración
            restore_record = BackupRestore.objects.create(
                tipo="RESTORE",
                estado="INICIADO",
                usuario=usuario,
                veterinaria=backup.veterinaria,
                motivo=motivo,
                ruta_archivo=backup.ruta_archivo,
                proveedor_almacenamiento="GCS",
            )
            
            # Guardar el ID del restore_record para re-crearlo si se pierde
            restore_record_id = restore_record.id_backup_restore
            
            try:
                if backup.estado != "EXITOSO":
                    raise ValueError("Solo se pueden restaurar backups exitosos")

                # Descargar de GCS
                dump_content = BackupService._download_from_gcs(backup.ruta_archivo)
                
                if scope == "GLOBAL" and getattr(usuario, "is_superuser", False):
                    # Restore completo de la base para superuser (todas las vets)
                    # Restaurar media primero, luego aplicar la BD.
                    # Así las filas de ArchivoClinico encuentran sus archivos en `MEDIA_ROOT`.
                    media_prefix = BackupService._media_backup_prefix_from_sql_blob_path(backup.ruta_archivo)
                    try:
                        restored_media_files = BackupService._restore_media_files_from_gcs(media_prefix)
                        if restored_media_files == 0:
                            BackupService._restore_legacy_media_zip_from_gcs(backup.ruta_archivo)
                    except Exception:
                        # Si el backup es anterior a este cambio, intenta recuperar el zip legacy.
                        BackupService._restore_legacy_media_zip_from_gcs(backup.ruta_archivo)

                    BackupService._restore_pg_dump(dump_content, None)
                    BackupService._reset_all_sequences_after_global_restore()
                elif veterinaria_id_target and getattr(usuario, "is_superuser", False):
                    # Restore solo una veterinaria desde un backup GLOBAL
                    # Snapshot de otras vets antes de restaurar
                    tenant_snapshots = BackupService._snapshot_other_veterinarias(
                        excluded_veterinaria_id=veterinaria_id_target,
                    )
                    executor_snapshot = BackupService._snapshot_user_state(usuario)

                    BackupService._restore_pg_dump(dump_content, None)
                    connection.close()

                    BackupService._restore_tenant_snapshots(tenant_snapshots)
                    BackupService._restore_user_state(executor_snapshot)
                else:
                    # Restore TENANT (scope="TENANT") para esa veterinaria
                    # Preserve la data actual de otras veterinarias y la cuenta del usuario ejecutor
                    tenant_snapshots = BackupService._snapshot_other_veterinarias(
                        excluded_veterinaria_id=backup.veterinaria.id_veterinaria,
                    )
                    executor_snapshot = BackupService._snapshot_user_state(usuario)

                    BackupService._restore_pg_dump(dump_content, backup.veterinaria.id_veterinaria)
                    connection.close()

                    BackupService._restore_tenant_snapshots(tenant_snapshots)
                    BackupService._restore_user_state(executor_snapshot)
                
                # Restaurar el historial que se perdió durante el psql
                table_name = BackupRestore._meta.db_table
                if BackupService._wait_for_table(table_name, timeout_seconds=60):
                    BackupService._restore_restore_history(restore_history)
                else:
                    logger.error(
                        "No se pudo restaurar BackupRestore: tabla no disponible tras restore"
                    )
                
                # Re-crear el registro del restore actual si se perdió
                table_name = BackupRestore._meta.db_table
                if BackupService._wait_for_table(table_name, timeout_seconds=60):
                        if not BackupRestore.objects.filter(id_backup_restore=restore_record_id).exists():
                            logger.warning(f"Restore record {restore_record_id} se perdió, recreando")
                            try:
                                BackupRestore.objects.create(
                                    id_backup_restore=restore_record_id,
                                    tipo="RESTORE",
                                    estado="INICIADO",
                                    usuario=usuario,
                                    veterinaria=backup.veterinaria,
                                    motivo=motivo,
                                    ruta_archivo=backup.ruta_archivo,
                                    proveedor_almacenamiento="GCS",
                                )
                            except IntegrityError:
                                # Otro proceso pudo haber insertado la fila entre el exists() y create();
                                # actualizar la fila existente en su lugar.
                                try:
                                    BackupRestore.objects.filter(id_backup_restore=restore_record_id).update(
                                        tipo="RESTORE",
                                        estado="INICIADO",
                                        usuario=usuario,
                                        veterinaria=backup.veterinaria,
                                        motivo=motivo,
                                        ruta_archivo=backup.ruta_archivo,
                                        proveedor_almacenamiento="GCS",
                                    )
                                except Exception:
                                    logger.exception(
                                        f"Fallo actualizando restore_record {restore_record_id} tras IntegrityError"
                                    )
                else:
                    logger.error(
                        "No se pudo comprobar/recrear restore_record: tabla BackupRestore no disponible"
                    )
                
                # Actualizar registro final de restore. Durante restore la conexión puede
                # reiniciarse o la fila quedar desincronizada, por eso usamos un guardado robusto.
                BackupService._safe_set_restore_status(
                    restore_record=restore_record,
                    estado="EXITOSO",
                    motivo=motivo,
                    hash_archivo=backup.hash_archivo,
                    backup=backup,
                    usuario=usuario,
                )
                
                # Registrar en bitácora
                BitacoraService.registrar_evento(
                    accion="BACKUP_RESTAURADO",
                    descripcion=f"Backup restaurado exitosamente para {backup.veterinaria.nombre}",
                    usuario=usuario,
                    request=request,
                    modulo="backups",
                    entidad_tipo="BackupRestore",
                    entidad_id=str(restore_record.id_backup_restore),
                    resultado="EXITO",
                    metadatos={
                        "veterinaria_id": backup.veterinaria.id_veterinaria,
                        "backup_original_id": backup_id,
                        "fecha_backup_original": str(backup.fecha_hora),
                        "scope": scope,
                        "veterinaria_target": veterinaria_id_target,
                    }
                )
                
                logger.info(f"Restauración exitosa para veterinaria {backup.veterinaria.id_veterinaria}")
                return True
                
            except Exception as e:
                logger.exception("Error detallado en restore_backup")
                
                # Restaurar el historial incluso si hubo error
                table_name = BackupRestore._meta.db_table
                if BackupService._wait_for_table(table_name, timeout_seconds=60):
                    BackupService._restore_restore_history(restore_history)
                else:
                    logger.error(
                        "No se pudo restaurar BackupRestore en handler de error: tabla no disponible"
                    )
                
                # Re-crear el registro del restore actual si se perdió
                table_name = BackupRestore._meta.db_table
                if BackupService._wait_for_table(table_name, timeout_seconds=60):
                    if not BackupRestore.objects.filter(id_backup_restore=restore_record_id).exists():
                        try:
                            BackupRestore.objects.create(
                                id_backup_restore=restore_record_id,
                                tipo="RESTORE",
                                estado="FALLIDO",
                                usuario=usuario,
                                veterinaria=backup.veterinaria,
                                motivo=f"Error en restauración: {str(e)}",
                                ruta_archivo=backup.ruta_archivo,
                                proveedor_almacenamiento="GCS",
                            )
                        except Exception as e2:
                                # Manejar race/duplicate key
                                if isinstance(e2, IntegrityError):
                                    try:
                                        BackupRestore.objects.filter(id_backup_restore=restore_record_id).update(
                                            estado="FALLIDO",
                                            motivo=f"Error en restauración: {str(e)}",
                                        )
                                    except Exception:
                                        logger.exception(
                                            f"No se pudo actualizar restore_record {restore_record_id} tras IntegrityError"
                                        )
                                else:
                                    logger.error(f"No se pudo recrear restore record en error handler: {str(e2)}")
                else:
                    logger.error(
                        "No se pudo recrear restore_record en error handler: tabla BackupRestore no disponible"
                    )
                
                BackupService._safe_set_restore_status(
                    restore_record=restore_record,
                    estado="FALLIDO",
                    motivo=f"Error en restauración: {str(e)}",
                    hash_archivo=None,
                    backup=backup,
                    usuario=usuario,
                )
                
                BitacoraService.registrar_evento(
                    accion="BACKUP_RESTAURACION_FALLIDA",
                    descripcion=f"Fallo al restaurar backup: {str(e)}",
                    usuario=usuario,
                    request=request,
                    modulo="backups",
                    resultado="FALLO",
                    metadatos={
                        "veterinaria_id": backup.veterinaria.id_veterinaria,
                        "backup_id": backup_id,
                        "error": str(e),
                    }
                )
                
                logger.error(f"Restauración fallida: {str(e)}")
                return False

        except BackupRestore.DoesNotExist:
            logger.error(f"Backup {backup_id} no encontrado o no es de tipo BACKUP")
            BitacoraService.registrar_evento(
                accion="BACKUP_NO_ENCONTRADO",
                descripcion=f"Backup ID {backup_id} no encontrado",
                usuario=usuario,
                request=request,
                modulo="backups",
                resultado="FALLO",
            )
            return False
        except Exception as e:
            logger.exception(f"Error inesperado en restore_backup: {str(e)}")
            return False

    @staticmethod
    def _safe_set_restore_status(
        restore_record: BackupRestore,
        estado: str,
        motivo: Optional[str],
        hash_archivo: Optional[str],
        backup: BackupRestore,
        usuario: Any,
    ) -> None:
        """
        Intenta persistir el estado final del restore incluso si la conexión quedó inestable
        tras ejecutar psql durante la restauración.
        """
        update_data = {
            "estado": estado,
            "motivo": motivo,
        }
        if hash_archivo is not None:
            update_data["hash_archivo"] = hash_archivo

        try:
            # Camino principal
            BackupRestore.objects.filter(
                id_backup_restore=restore_record.id_backup_restore
            ).update(**update_data)
            return
        except Exception:
            logger.exception("Fallo actualización primaria de estado restore; reintentando con nueva conexión")

        try:
            # Reabrir conexión por si el restore invalidó la sesión actual
            connection.close()
            updated = BackupRestore.objects.filter(
                id_backup_restore=restore_record.id_backup_restore
            ).update(**update_data)

            if updated:
                return

            # Si la fila no existe tras restore, crear un registro consistente final.
            BackupRestore.objects.create(
                tipo="RESTORE",
                estado=estado,
                usuario=usuario,
                veterinaria=backup.veterinaria,
                motivo=motivo or "Restauración manual",
                proveedor_almacenamiento="GCS",
                hash_archivo=hash_archivo,
            )
        except Exception:
            logger.exception("No se pudo persistir estado final de restore")

    @staticmethod
    def _safe_update_backup_record(record: BackupRestore, updates: Dict[str, Any], retries: int = 3, delay: float = 1.0) -> None:
        """
        Intenta actualizar un registro `BackupRestore` con reintentos para cubrir
        casos donde la conexión DB pudo haberse invalidado (p.ej. tras subprocess).
        """
        attempt = 0
        last_exc = None
        while attempt < retries:
            try:
                # Reabrir conexión antes de intentar
                try:
                    connection.close()
                except Exception:
                    pass

                for k, v in updates.items():
                    setattr(record, k, v)

                record.save()
                return
            except Exception as e:
                last_exc = e
                logger.warning(
                    "Intento %s de persistir BackupRestore %s falló: %s",
                    attempt + 1,
                    getattr(record, 'id_backup_restore', 'unknown'),
                    str(e),
                )
                attempt += 1
                time.sleep(delay)

        logger.exception("No se pudo actualizar BackupRestore tras %s intentos: %s", retries, str(last_exc))

    @staticmethod
    def _sanitize_instances_for_serialization(instances: list[models.Model]) -> list[models.Model]:
        """
        Limpia instancias para asegurar que todos los campos tengan valores que Django pueda serializar.
        Maneja casos donde BinaryFields u otros campos tienen dicts en lugar de bytes.
        """
        sanitized = []
        for instance in instances:
            try:
                # Verificar cada campo para valores problemáticos
                for field in instance._meta.get_fields():
                    if not field.concrete:
                        continue
                    
                    try:
                        value = getattr(instance, field.name, None)
                        
                        # Si es BinaryField y tiene dict/list, vaciar o convertir
                        if field.get_internal_type() == 'BinaryField' and isinstance(value, (dict, list)):
                            logger.debug(
                                f"Campo BinaryField {field.name} en {instance._meta.label} tiene {type(value).__name__}, limpiando"
                            )
                            setattr(instance, field.name, b"")
                        
                        # Si es JSONField pero tiene bytes, dejar como está (Django lo maneja)
                        # Si es CharField/TextField con objeto no-string, convertir
                        elif field.get_internal_type() in ('CharField', 'TextField') and value and not isinstance(value, str):
                            if isinstance(value, bytes):
                                setattr(instance, field.name, value.decode('utf-8', errors='replace'))
                            else:
                                setattr(instance, field.name, str(value))
                    
                    except Exception as e:
                        logger.debug(f"Error limpiando campo {field.name}: {str(e)}")
                        continue
                
                sanitized.append(instance)
            except Exception as e:
                logger.warning(f"Error sanitizando instancia {instance._meta.label}: {str(e)}")
                continue
        
        return sanitized

    @staticmethod
    def _snapshot_other_veterinarias(excluded_veterinaria_id: int) -> Dict[str, Any]:
        """
        Captura el estado actual de todas las veterinarias excepto la que se va a restaurar.
        Se usa para re-aplicar la data de otras clínicas después de un restore global.
        """
        snapshots = []
        veterinarias = list(Veterinaria.objects.exclude(id_veterinaria=excluded_veterinaria_id).order_by(
            "id_veterinaria"
        ))
        
        total_vets = len(veterinarias)
        logger.info(f"Capturando snapshots de {total_vets} veterinarias")

        for vet_idx, veterinaria in enumerate(veterinarias, 1):
            try:
                logger.debug(f"[{vet_idx}/{total_vets}] Snapshot de veterinaria {veterinaria.id_veterinaria}")
                
                instances = BackupService._collect_related_instances(veterinaria)
                if not instances:
                    logger.debug(f"Sin instancias para veterinaria {veterinaria.id_veterinaria}")
                    continue
                
                logger.debug(f"Recolectadas {len(instances)} instancias para veterinaria {veterinaria.id_veterinaria}")
                
                # Sanitizar instancias antes de serializar
                sanitized_instances = BackupService._sanitize_instances_for_serialization(instances)
                if not sanitized_instances:
                    logger.warning(f"Instancias de veterinaria {veterinaria.id_veterinaria} fallaron al sanitizar")
                    continue
                
                logger.debug(f"Sanitizadas {len(sanitized_instances)} instancias")
                
                # Serializar con manejo de errores
                try:
                    serialized_data = serializers.serialize("json", sanitized_instances)
                    logger.debug(f"Serializado snapshot de veterinaria {veterinaria.id_veterinaria} ({len(serialized_data)} bytes)")
                except Exception as e:
                    logger.warning(
                        f"Error serializando snapshot de veterinaria {veterinaria.id_veterinaria}: {str(e)}"
                    )
                    # Intenta con fewer fields si es necesario
                    try:
                        # Fallback: serializar solo modelos "seguros" sin relaciones complejas
                        safe_instances = [inst for inst in sanitized_instances if not hasattr(inst, 'raw_data')]
                        if safe_instances:
                            logger.debug(f"Reintentando con {len(safe_instances)} instancias seguras")
                            serialized_data = serializers.serialize("json", safe_instances)
                        else:
                            logger.warning(f"No hay instancias seguras para veterinaria {veterinaria.id_veterinaria}")
                            continue
                    except Exception as e2:
                        logger.warning(f"Fallback serialization también falló: {str(e2)}")
                        continue
                
                snapshots.append(
                    {
                        "veterinaria_id": veterinaria.id_veterinaria,
                        "data": serialized_data,
                    }
                )
                logger.info(f"Snapshot {vet_idx}/{total_vets} capturado exitosamente para veterinaria {veterinaria.id_veterinaria}")
                
            except Exception as e:
                logger.warning(
                    f"Error capturando snapshot de veterinaria {veterinaria.id_veterinaria}: {str(e)}"
                )
                continue

        logger.info(f"Snapshots capturados: {len(snapshots)}/{total_vets} veterinarias")
        return {"tenants": snapshots}

    @staticmethod
    def _snapshot_user_state(usuario: Any) -> Optional[Dict[str, Any]]:
        """
        Captura el estado del usuario que ejecuta la restauración para no perder sus permisos.
        """
        if not getattr(usuario, "pk", None):
            return None

        current_user = type(usuario).objects.select_related("role", "veterinaria").prefetch_related(
            "groups",
            "user_permissions",
        ).get(pk=usuario.pk)

        return {
            "correo": current_user.correo,
            "fields": {
                "role_id": current_user.role_id,
                "veterinaria_id": current_user.veterinaria_id,
                "is_active": current_user.is_active,
                "is_staff": current_user.is_staff,
                "is_superuser": current_user.is_superuser,
                "password": current_user.password,
                "last_login": current_user.last_login,
                "date_joined": current_user.date_joined,
            },
            "groups": list(current_user.groups.values_list("pk", flat=True)),
            "user_permissions": list(current_user.user_permissions.values_list("pk", flat=True)),
        }

    @staticmethod
    def _collect_related_instances(root_instance: models.Model) -> list[models.Model]:
        """
        Recolecta recursivamente el árbol de objetos relacionados a una veterinaria.
        Excluye modelos que no necesitan ser restaurados (ej: auditoría, logs).
        """
        # Modelos a excluir del snapshot (auditoría, logs, etc)
        EXCLUDED_MODELS = {
            "AutenticacionySeguridad.Bitacora",
            "AutenticacionySeguridad.BitacoraAuditoria",
            "AutenticacionySeguridad.Log",
            "AutenticacionySeguridad.LogEvent",
        }
        
        queue: deque[models.Model] = deque([root_instance])
        visited: set[tuple[str, Any]] = set()
        ordered_instances: list[models.Model] = []

        while queue:
            instance = queue.popleft()
            instance_key = (instance._meta.label_lower, instance.pk)
            
            # Excluir modelos auditables
            if instance._meta.label in EXCLUDED_MODELS:
                logger.debug(f"Excluida instancia {instance._meta.label} del snapshot (auditoría)")
                continue
            
            if instance_key in visited:
                continue

            visited.add(instance_key)
            ordered_instances.append(instance)

            for field in instance._meta.get_fields():
                if not getattr(field, "auto_created", False) or getattr(field, "concrete", True):
                    continue

                if getattr(field, "many_to_many", False):
                    continue

                accessor_name = field.get_accessor_name()
                try:
                    related_value = getattr(instance, accessor_name)
                except Exception:
                    continue

                if getattr(field, "one_to_one", False):
                    try:
                        related_instance = related_value
                    except Exception:
                        related_instance = None

                    if related_instance is not None and related_instance._meta.label not in EXCLUDED_MODELS:
                        queue.append(related_instance)
                    continue

                try:
                    for related_instance in related_value.all():
                        if related_instance._meta.label not in EXCLUDED_MODELS:
                            queue.append(related_instance)
                except Exception:
                    continue

        return ordered_instances

    @staticmethod
    def _restore_tenant_snapshots(snapshot_payload: Dict[str, Any]) -> None:
        """
        Reaplica la data de las otras veterinarias luego de restaurar el backup objetivo.
        Incluye validación robusta de tipos y manejo de errores.
        """
        tenant_snapshots = snapshot_payload.get("tenants", []) if snapshot_payload else []
        restored_models: list[type[models.Model]] = []

        with transaction.atomic():
            for idx, tenant_snapshot in enumerate(tenant_snapshots):
                try:
                    # Extraer data del snapshot
                    if isinstance(tenant_snapshot, dict):
                        raw_data = tenant_snapshot.get("data")
                    else:
                        # Si el snapshot completo es la data (fallback)
                        raw_data = tenant_snapshot
                    
                    if not raw_data:
                        logger.warning(f"Snapshot {idx} vacío, saltando")
                        continue
                    
                    logger.debug(f"Snapshot {idx} raw_data type: {type(raw_data).__name__}")
                    
                    # Normalizar payload a JSON string
                    try:
                        payload = BackupService._normalize_json_payload(raw_data)
                    except ValueError as e:
                        logger.error(f"Fallo normalizar snapshot {idx}: {str(e)}", exc_info=True)
                        # Continuar con siguiente snapshot en lugar de fallar todo
                        continue
                    
                    # Validar que payload es string
                    if not isinstance(payload, str):
                        logger.error(
                            f"Payload de snapshot {idx} no es string: {type(payload).__name__}. "
                            f"Intentando conversión final."
                        )
                        payload = str(payload)
                    
                    logger.debug(f"Snapshot {idx} payload length: {len(payload)} chars")
                    
                    # Deserializar con manejo de errores por objeto
                    try:
                        objects = list(serializers.deserialize("json", payload))
                        logger.info(f"Snapshot {idx} deserializado: {len(objects)} objetos")
                    except Exception as e:
                        logger.error(
                            f"Fallo deserializar snapshot {idx}: {str(e)}. "
                            f"Payload primeros 200 chars: {payload[:200]}",
                            exc_info=True
                        )
                        # Intenta parsear payload como JSON e iterar sobre objetos individuales
                        try:
                            import json as json_lib
                            json_data = json_lib.loads(payload)
                            if isinstance(json_data, list):
                                logger.info(f"Reintentando deserialización individual de {len(json_data)} objetos")
                                objects = []
                                for obj_idx, obj_data in enumerate(json_data):
                                    try:
                                        single_obj_str = json_lib.dumps([obj_data])
                                        deserialized = list(serializers.deserialize("json", single_obj_str))
                                        if deserialized:
                                            objects.extend(deserialized)
                                    except Exception as e2:
                                        logger.warning(
                                            f"Objeto {obj_idx} en snapshot {idx} no se pudo deserializar: {str(e2)}"
                                        )
                                        continue
                                if not objects:
                                    logger.error(f"Ningún objeto en snapshot {idx} se pudo deserializar, saltando")
                                    continue
                            else:
                                logger.error(f"Payload no es lista de JSON, saltando snapshot {idx}")
                                continue
                        except Exception as e2:
                            logger.error(
                                f"Reintento de deserialización individual también falló: {str(e2)}",
                                exc_info=True
                            )
                            continue
                    
                    # Guardar objetos
                    saved_count = 0
                    for save_idx, obj in enumerate(objects):
                        try:
                            restored_models.append(obj.object.__class__)
                            obj.save()
                            saved_count += 1
                        except Exception as e:
                            logger.warning(
                                f"Error guardando objeto {save_idx} en snapshot {idx}: {str(e)}"
                            )
                            continue
                    
                    logger.info(f"Snapshot {idx} restaurado: {saved_count}/{len(objects)} objetos guardados")
                    
                except Exception as e:
                    logger.error(
                        f"Error restaurando snapshot {idx}: {str(e)}",
                        exc_info=True
                    )
                    # Continuar con siguiente snapshot
                    continue

            BackupService._reset_sequences(restored_models)

    @staticmethod
    def _restore_user_state(snapshot: Optional[Dict[str, Any]]) -> None:
        """
        Reaplica el usuario que ejecutó la restauración conservando contraseña y permisos.
        """
        if not snapshot:
            return

        try:
            user = getattr(BackupService, "_user_model", None)
            if user is None:
                from ..models.user import User as UserModel

                BackupService._user_model = UserModel
                user = UserModel

            restored_user = user.objects.select_related("role", "veterinaria").prefetch_related(
                "groups",
                "user_permissions",
            ).get(correo=snapshot["correo"])

            fields = snapshot["fields"]
            restored_user.role_id = fields.get("role_id")
            restored_user.veterinaria_id = fields.get("veterinaria_id")
            restored_user.is_active = fields.get("is_active", restored_user.is_active)
            restored_user.is_staff = fields.get("is_staff", restored_user.is_staff)
            restored_user.is_superuser = fields.get("is_superuser", restored_user.is_superuser)
            restored_user.password = fields.get("password", restored_user.password)
            restored_user.last_login = fields.get("last_login")
            restored_user.date_joined = fields.get("date_joined", restored_user.date_joined)
            restored_user.save()

            restored_user.groups.set(snapshot.get("groups", []))
            restored_user.user_permissions.set(snapshot.get("user_permissions", []))

        except Exception as e:
            logger.warning(f"No se pudo restaurar el usuario ejecutor: {str(e)}")

    @staticmethod
    def _reset_sequences(model_classes: list[type[models.Model]]) -> None:
        """
        Ajusta las secuencias de AutoField después de reinsertar datos con PK explícita.
        """
        existing_tables = set()
        try:
            existing_tables = set(connection.introspection.table_names())
        except Exception:
            logger.debug("No se pudo obtener la lista de tablas existentes para reset de secuencias")

        unique_models = []
        seen = set()
        for model_class in model_classes:
            if model_class in seen:
                continue
            seen.add(model_class)

            table_name = getattr(getattr(model_class, "_meta", None), "db_table", None)
            if existing_tables and table_name and table_name not in existing_tables:
                continue

            unique_models.append(model_class)

        if not unique_models:
            return

        sql_statements = connection.ops.sequence_reset_sql(no_style(), unique_models)
        if not sql_statements:
            return

        with connection.cursor() as cursor:
            for sql in sql_statements:
                try:
                    cursor.execute(sql)
                except Exception as exc:
                    logger.warning(
                        "No se pudo recalibrar una secuencia tras restore: %s", str(exc)
                    )
                    continue

    @staticmethod
    def _reset_all_sequences_after_global_restore() -> None:
        """
        Recalibra las secuencias de todos los modelos gestionados después de un restore GLOBAL.
        """
        try:
            model_classes = []
            for model_class in apps.get_models():
                meta = getattr(model_class, "_meta", None)
                if not meta or not getattr(meta, "managed", True) or getattr(meta, "proxy", False):
                    continue
                model_classes.append(model_class)

            BackupService._reset_sequences(model_classes)
        except Exception:
            logger.exception("No se pudieron recalibrar las secuencias tras restore GLOBAL")

    @staticmethod
    def _generate_pg_dump(veterinaria_id: Optional[int]) -> str:
        """
        Genera un dump SQL de PostgreSQL usando pg_dump.
        Retorna el contenido como string.
        """
        db_url = settings.DATABASES["default"]["ENGINE"]
        db_name = settings.DATABASES["default"]["NAME"]
        db_user = settings.DATABASES["default"]["USER"]
        db_password = settings.DATABASES["default"]["PASSWORD"]
        db_host = settings.DATABASES["default"]["HOST"]
        db_port = settings.DATABASES["default"]["PORT"]

        pg_dump_executable = BackupService._resolve_postgres_executable(
            getattr(settings, "PG_DUMP_PATH", "pg_dump"),
            "pg_dump.exe",
        )

        # Construir comando pg_dump
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password or ""

        cmd = [
            pg_dump_executable,
            "-h", db_host or "localhost",
            "-p", str(db_port or 5432),
            "-U", db_user,
            "-F", "p",  # formato plain text
            "--clean",
            "--if-exists",
            "-v",
            db_name,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=300,  # 5 minutos máximo
                check=True,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            raise Exception("pg_dump timeout después de 5 minutos")
        except subprocess.CalledProcessError as e:
            raise Exception(f"pg_dump error: {e.stderr}")
        except FileNotFoundError:
            raise Exception(
                f"pg_dump no encontrado en PATH. Revisa PG_DUMP_PATH={pg_dump_executable} "
                "o instala PostgreSQL client tools"
            )

    @staticmethod
    def _restore_pg_dump(dump_content: str, veterinaria_id: int) -> None:
        """
        Restaura un dump SQL en PostgreSQL usando psql.
        """
        db_url = settings.DATABASES["default"]["ENGINE"]
        db_name = settings.DATABASES["default"]["NAME"]
        db_user = settings.DATABASES["default"]["USER"]
        db_password = settings.DATABASES["default"]["PASSWORD"]
        db_host = settings.DATABASES["default"]["HOST"]
        db_port = settings.DATABASES["default"]["PORT"]

        env = os.environ.copy()
        env["PGPASSWORD"] = db_password or ""

        psql_executable = BackupService._resolve_postgres_executable(
            getattr(settings, "PSQL_PATH", "psql"),
            "psql.exe",
        )

        cmd = [
            psql_executable,
            "-h", db_host or "localhost",
            "-p", str(db_port or 5432),
            "-U", db_user,
            "-d", db_name,
            "-v", "ON_ERROR_STOP=on",
        ]

        normalized_dump = BackupService._coerce_dump_content(dump_content)
        
        # Validar que normalized_dump es string
        if not isinstance(normalized_dump, str):
            logger.error(
                f"normalized_dump no es string después de _coerce_dump_content: {type(normalized_dump).__name__}"
            )
            raise TypeError(
                f"Dump content debe ser string, obtuvo {type(normalized_dump).__name__}"
            )

        # Para restores globales (veterinaria_id is None) quitamos sentencias de schema
        # peligrosas que podrían eliminar tablas críticas de la aplicación.
        initial_input = normalized_dump
        if veterinaria_id is None:
            try:
                initial_input = BackupService._strip_schema_statements(normalized_dump)
                initial_input = BackupService._strip_sequence_statements(initial_input)
            except Exception:
                initial_input = normalized_dump

        try:
            result = subprocess.run(
                cmd,
                input=initial_input,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=600,  # 10 minutos máximo
                check=True,
            )
            logger.info(f"Restauración completada para veterinaria {veterinaria_id}")
        except subprocess.TimeoutExpired:
            raise Exception("psql timeout después de 10 minutos")
        except subprocess.CalledProcessError as e:
            error_text = (e.stderr or e.stdout or "").lower()

            # Compatibilidad con backups antiguos sin --clean/--if-exists.
            # Si el script falla por objetos existentes, limpiamos schema public
            # y reintentamos una sola vez.
            if "already exists" in error_text or "ya existe" in error_text:
                logger.warning(
                    "Restore falló por objetos existentes; intentando reintento seguro"
                )
                # Para GLOBAL no limpiamos todo el schema; intentamos sanear el dump
                if veterinaria_id is None:
                    # Quitar sentencias de schema y reintentar sin dropear public
                    safe_dump = BackupService._strip_schema_statements(normalized_dump)
                    safe_dump = BackupService._strip_sequence_statements(safe_dump)
                    retry = subprocess.run(
                        cmd,
                        input=safe_dump,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=env,
                        timeout=600,
                    )
                    if retry.returncode == 0:
                        logger.info(
                            f"Restauración completada en reintento seguro para veterinaria {veterinaria_id}"
                        )
                        return

                    # Si el reintento falló por objetos existentes, intentamos crear
                    # una versión idempotente del dump (CREATE ... IF NOT EXISTS)
                    idemp_dump, idemp_count = BackupService._make_create_statements_idempotent(safe_dump)
                    if idemp_count > 0:
                        logger.warning(
                            "Intentando reintento con CREATE ... IF NOT EXISTS (%s reemplazos)", idemp_count
                        )
                        retry_idemp = subprocess.run(
                            cmd,
                            input=idemp_dump,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            env=env,
                            timeout=600,
                        )
                        if retry_idemp.returncode == 0:
                            logger.info(
                                f"Restauración completada usando CREATE IF NOT EXISTS para veterinaria {veterinaria_id}"
                            )
                            return

                        # si sigue fallando, usar el texto de este intento para diagnosticar
                        retry = retry_idemp

                    retry_error_text = (retry.stderr or retry.stdout or "").lower()
                    if "permission denied to change default privileges" in retry_error_text:
                        sanitized_dump, removed_statements = BackupService._strip_default_privileges_statements(
                            idemp_dump if idemp_count > 0 else safe_dump
                        )
                        if removed_statements > 0:
                            logger.warning(
                                "Restore falló por default privileges; se reintentará quitando %s sentencias ALTER DEFAULT PRIVILEGES",
                                removed_statements,
                            )
                            retry_sanitized = subprocess.run(
                                cmd,
                                input=sanitized_dump,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                                env=env,
                                timeout=600,
                            )
                            if retry_sanitized.returncode == 0:
                                logger.info(
                                    "Restauración completada en tercer intento tras sanear ALTER DEFAULT PRIVILEGES"
                                )
                                return
                            raise Exception(
                                f"psql error (reintento saneado): {retry_sanitized.stderr or retry_sanitized.stdout}"
                            )

                    # Si todavía falla por 'already exists', intentar remover las
                    # sentencias CREATE relacionadas con el/los objetos mencionados
                    already_exists_matches = re.findall(r"relation \"([^\"]+)\" already exists", (retry.stderr or retry.stdout or ""), flags=re.IGNORECASE)
                    if already_exists_matches:
                        cleaned_dump, removals = BackupService._remove_create_statements_for_names(
                            idemp_dump if locals().get('idemp_dump') is not None else safe_dump,
                            already_exists_matches,
                        )
                        cleaned_dump = BackupService._strip_sequence_statements(cleaned_dump)
                        if removals > 0:
                            logger.warning(f"Eliminadas {removals} sentencias CREATE que mencionaban objetos existentes; reintentando")
                            retry_removed = subprocess.run(
                                cmd,
                                input=cleaned_dump,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                                env=env,
                                timeout=600,
                            )
                            if retry_removed.returncode == 0:
                                logger.info(
                                    f"Restauración completada tras eliminar CREATE statements conflictivos para veterinaria {veterinaria_id}"
                                )
                                return
                            # actualizar retry para mensaje de error final
                            retry = retry_removed

                    # Como último recurso para restores GLOBAL: realizar un reset
                    # del schema public (DROP SCHEMA public CASCADE; CREATE SCHEMA public;)
                    # y reintentar con el dump original para restablecer la BD tal cual.
                    try:
                        if veterinaria_id is None:
                            logger.warning("Reintento final: limpiando schema public para aplicar restore GLOBAL tal cual")
                            BackupService._reset_public_schema(psql_executable, db_host, db_port, db_user, db_name, env)
                            final_dump = BackupService._strip_default_privileges_statements(normalized_dump)[0]
                            final_retry = subprocess.run(
                                cmd,
                                input=final_dump,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                                env=env,
                                timeout=900,
                            )
                            if final_retry.returncode == 0:
                                logger.info(
                                    f"Restauración completada tras limpiar schema public para veterinaria {veterinaria_id}"
                                )
                                return
                            raise Exception(f"psql error (reintento final tras reset): {final_retry.stderr or final_retry.stdout}")
                    except Exception:
                        # Si el reset o el reintento final fallan, propagar el error original
                        logger.exception("Fallo en reintento final con reset de schema public")
                    raise Exception(f"psql error (reintento seguro): {retry.stderr or retry.stdout}")
                else:
                    # Comportamiento previo para restores por veterinaria
                    BackupService._reset_public_schema(psql_executable, db_host, db_port, db_user, db_name, env)
                    retry = subprocess.run(
                        cmd,
                        input=normalized_dump,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=env,
                        timeout=600,
                    )
                    if retry.returncode == 0:
                        logger.info(
                            f"Restauración completada en reintento para veterinaria {veterinaria_id}"
                        )
                        return

                    retry_error_text = (retry.stderr or retry.stdout or "").lower()
                    if "permission denied to change default privileges" in retry_error_text:
                        sanitized_dump, removed_statements = BackupService._strip_default_privileges_statements(
                            normalized_dump
                        )
                        if removed_statements > 0:
                            logger.warning(
                                "Restore falló por default privileges; se reintentará quitando %s sentencias ALTER DEFAULT PRIVILEGES",
                                removed_statements,
                            )
                            BackupService._reset_public_schema(psql_executable, db_host, db_port, db_user, db_name, env)
                            retry_sanitized = subprocess.run(
                                cmd,
                                input=sanitized_dump,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                                env=env,
                                timeout=600,
                            )
                            if retry_sanitized.returncode == 0:
                                logger.info(
                                    "Restauración completada en tercer intento tras sanear ALTER DEFAULT PRIVILEGES"
                                )
                                return
                            raise Exception(
                                f"psql error (reintento saneado): {retry_sanitized.stderr or retry_sanitized.stdout}"
                            )

                    raise Exception(f"psql error (reintento): {retry.stderr or retry.stdout}")

            raise Exception(f"psql error: {e.stderr}")
        except FileNotFoundError:
            raise Exception(
                f"psql no encontrado en PATH. Revisa PSQL_PATH={psql_executable} "
                "o instala PostgreSQL client tools"
            )

    @staticmethod
    def _reset_public_schema(psql_executable: str, db_host: str, db_port: Any, db_user: str, db_name: str, env: Dict[str, str]) -> None:
        """
        Limpia completamente el schema public para permitir un restore completo
        cuando un dump antiguo no trae DROP statements.
        """
        reset_cmd = [
            psql_executable,
            "-h", db_host or "localhost",
            "-p", str(db_port or 5432),
            "-U", db_user,
            "-d", db_name,
            "-v", "ON_ERROR_STOP=on",
            "-c", "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;",
        ]

        reset_result = subprocess.run(
            reset_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=120,
        )

        if reset_result.returncode != 0:
            raise Exception(
                f"No se pudo limpiar schema public antes del reintento: {reset_result.stderr or reset_result.stdout}"
            )

    @staticmethod
    def _strip_default_privileges_statements(dump_sql: str) -> tuple[str, int]:
        """
        Quita sentencias ALTER DEFAULT PRIVILEGES que suelen fallar por permisos
        al restaurar en entornos donde el rol actual no es dueño de esos objetos.
        """
        pattern = re.compile(r"ALTER\s+DEFAULT\s+PRIVILEGES[\s\S]*?;", re.IGNORECASE)
        sanitized, removed = pattern.subn("", dump_sql)
        return sanitized, removed

    @staticmethod
    def _strip_sequence_statements(dump_sql: str) -> str:
        """
        Elimina CREATE SEQUENCE y ALTER SEQUENCE del dump para evitar colisiones
        con secuencias ya existentes durante restores GLOBAL.
        """
        try:
            patterns = [
                r"(?ims)^\s*CREATE\s+SEQUENCE\s+.*?;\s*",
                r"(?ims)^\s*ALTER\s+SEQUENCE\s+.*?;\s*",
            ]
            result = dump_sql
            for p in patterns:
                result = re.sub(p, "", result)
            return result
        except Exception:
            logger.exception("Fallo eliminando sentencias de secuencia en dump")
            return dump_sql

    @staticmethod
    def _make_create_statements_idempotent(dump_sql: str) -> tuple[str, int]:
        """
        Transforma sentencias CREATE (TABLE, INDEX, SEQUENCE, TYPE) para añadir
        IF NOT EXISTS cuando sea posible, reduciendo errores 'already exists'
        durante restores GLOBAL.
        Retorna (sanitized_sql, replacements_count).
        """
        try:
            original = dump_sql
            count = 0

            # CREATE TABLE -> CREATE TABLE IF NOT EXISTS
            pattern_table = re.compile(r"(^\s*CREATE\s+TABLE\s+)(?!IF\s+NOT\s+EXISTS)", re.IGNORECASE | re.MULTILINE)
            dump_sql, n = pattern_table.subn(lambda m: m.group(1) + "IF NOT EXISTS ", dump_sql)
            count += n

            # CREATE SEQUENCE -> CREATE SEQUENCE IF NOT EXISTS
            pattern_seq = re.compile(r"(^\s*CREATE\s+SEQUENCE\s+)(?!IF\s+NOT\s+EXISTS)", re.IGNORECASE | re.MULTILINE)
            dump_sql, n = pattern_seq.subn(lambda m: m.group(1) + "IF NOT EXISTS ", dump_sql)
            count += n

            # CREATE TYPE -> CREATE TYPE IF NOT EXISTS
            pattern_type = re.compile(r"(^\s*CREATE\s+TYPE\s+)(?!IF\s+NOT\s+EXISTS)", re.IGNORECASE | re.MULTILINE)
            dump_sql, n = pattern_type.subn(lambda m: m.group(1) + "IF NOT EXISTS ", dump_sql)
            count += n

            # CREATE INDEX and CREATE UNIQUE INDEX (attempt IF NOT EXISTS)
            pattern_index = re.compile(r"(^\s*CREATE\s+(?:UNIQUE\s+)?INDEX\s+)(?!IF\s+NOT\s+EXISTS)", re.IGNORECASE | re.MULTILINE)
            dump_sql, n = pattern_index.subn(lambda m: m.group(1) + "IF NOT EXISTS ", dump_sql)
            count += n

            # Return sanitized and count
            return dump_sql, count
        except Exception:
            logger.exception("Fallo creando versiones idempotentes de CREATE statements")
            return dump_sql, 0

    @staticmethod
    def _remove_create_statements_for_names(dump_sql: str, names: list[str]) -> tuple[str, int]:
        """
        Elimina del dump las sentencias CREATE que mencionan los nombres proporcionados.
        Útil como último recurso para evitar errores 'relation "..." already exists'
        transformando el dump para que no intente crear objetos que ya existen.
        Retorna (nuevo_dump, removals_count).
        """
        try:
            new_sql = dump_sql
            removed = 0
            for name in names:
                # Eliminar CREATE SEQUENCE/TABLE/INDEX/TYPE que contienen el nombre
                pattern = re.compile(rf"(?is)(?:CREATE\s+(?:SEQUENCE|TABLE|INDEX|TYPE)[^;]*\b{re.escape(name)}\b[^;]*;)" )
                new_sql, n = pattern.subn("", new_sql)
                removed += n

                # También intentar eliminar OWNER/OWNED BY/SETVAL relacionados
                pattern2 = re.compile(rf"(?is)(?:ALTER\s+SEQUENCE[^;]*\b{re.escape(name)}\b[^;]*;)")
                new_sql, n2 = pattern2.subn("", new_sql)
                removed += n2

            return new_sql, removed
        except Exception:
            logger.exception("Fallo eliminando CREATE statements por nombre")
            return dump_sql, 0

    @staticmethod
    def _strip_schema_statements(dump_sql: str) -> str:
        """
        Elimina sentencias peligrosas de esquema que pueden borrar tablas críticas
        durante un restore global, por ejemplo `DROP SCHEMA public CASCADE;`
        y `CREATE SCHEMA public;`. Esto se aplica solo en restores GLOBAL para
        evitar perder tablas de la aplicación como `backup_restore` o `usuarios`.
        """
        try:
            # Quitar DROP/CREATE schema public y statements relacionados
            patterns = [
                r"DROP\s+SCHEMA\s+public\s+CASCADE;",
                r"CREATE\s+SCHEMA\s+public;",
                r"SET\s+search_path\s*=\s*public,\s*pg_catalog;",
            ]
            result = dump_sql
            for p in patterns:
                result = re.sub(p, "", result, flags=re.IGNORECASE)
            return result
        except Exception:
            logger.exception("Fallo sanitizando sentencias de schema en dump")
            return dump_sql

    @staticmethod
    def _coerce_dump_content(dump_content: Any) -> str:
        """
        Normaliza contenido de dump a texto SQL para psql.
        Soporta strings, bytes y dicts (caso observado en restauraciones fallidas).
        """
        if isinstance(dump_content, str):
            return dump_content

        if isinstance(dump_content, (bytes, bytearray)):
            return bytes(dump_content).decode("utf-8", errors="replace")

        if isinstance(dump_content, dict):
            for key in ("sql", "content", "data", "dump"):
                value = dump_content.get(key)
                if isinstance(value, str):
                    return value
                if isinstance(value, (bytes, bytearray)):
                    return bytes(value).decode("utf-8", errors="replace")
            return json.dumps(dump_content, ensure_ascii=False)

        return str(dump_content)

    @staticmethod
    def _normalize_json_payload(payload: Any) -> str:
        """
        Convierte payloads de snapshot a JSON string compatible con serializers.deserialize.
        Valida que la salida sea siempre un string JSON válido.
        """
        if isinstance(payload, str):
            # Validar que sea JSON válido
            try:
                json.loads(payload)
                return payload
            except json.JSONDecodeError as e:
                logger.warning(f"JSON string inválido en payload: {str(e)}, intentando reprocesar")
                # Si es inválido, intenta como dict o bytes
                return BackupService._normalize_json_payload(payload.encode())
        if isinstance(payload, (bytes, bytearray)):
            try:
                decoded = bytes(payload).decode("utf-8", errors="replace")
                # Validar que el resultado decodificado sea JSON válido
                json.loads(decoded)
                return decoded
            except json.JSONDecodeError as e:
                logger.warning(f"JSON en bytes inválido: {str(e)}")
                # Intenta como dict si es posible
                return BackupService._normalize_json_payload(decoded)
        if isinstance(payload, (dict, list)):
            try:
                # Intenta serializar a JSON string
                result = json.dumps(payload, ensure_ascii=False, default=str)
                # Valida que sea deserializable
                json.loads(result)
                return result
            except (TypeError, ValueError) as e:
                logger.error(f"No se puede serializar payload a JSON: {str(e)}", exc_info=True)
                raise ValueError(f"Payload no es JSON-serializable: {str(e)}")
        # Último intento: convertir a string y serializar como JSON
        try:
            return json.dumps(str(payload), ensure_ascii=False)
        except Exception as e:
            logger.error(f"Fallo final en normalización de payload: {str(e)}", exc_info=True)
            raise ValueError(f"No se puede normalizar payload: {str(e)}")

    @staticmethod
    def _upload_to_gcs(
        filename: str,
        content: str,
        veterinaria_id: int,
        scope: str = "TENANT",
    ) -> str:
        """
        Sube un archivo a Google Cloud Storage.
        Retorna la ruta remota.
        """
        try:
            # Validar y normalizar content
            if not isinstance(content, str):
                logger.warning(
                    f"Content no es string en _upload_to_gcs (tipo: {type(content).__name__}), normalizando"
                )
                content = BackupService._coerce_dump_content(content)
            
            if not isinstance(content, str):
                raise TypeError(
                    f"Content debe ser string después de normalización, obtuvo {type(content).__name__}"
                )
            
            bucket_name = getattr(settings, "GCS_BUCKET_NAME", None)
            if not bucket_name:
                raise ValueError("GCS_BUCKET_NAME no configurado en settings")

            client = BackupService._get_storage_client()
            bucket = client.bucket(bucket_name)
            
            # Prefijo por veterinaria o global para organización
            prefix = getattr(settings, "GCS_BACKUP_PREFIX", "backups")
            scope = str(scope or "TENANT").upper()
            if scope == "GLOBAL":
                blob_name = f"{prefix}/global/{filename}"
            else:
                blob_name = f"{prefix}/veterinaria_{veterinaria_id}/{filename}"
            blob = bucket.blob(blob_name)
            
            blob.upload_from_string(
                content,
                content_type="text/plain",
                timeout=600,
            )
            
            logger.info(f"Archivo subido a GCS: {blob_name}")
            return blob_name
            
        except Exception as e:
            logger.error(f"Error subiendo a GCS: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _download_from_gcs(blob_path: str) -> str:
        """
        Descarga un archivo desde Google Cloud Storage.
        Retorna el contenido como string.
        """
        try:
            bucket_name = getattr(settings, "GCS_BUCKET_NAME", None)
            if not bucket_name:
                raise ValueError("GCS_BUCKET_NAME no configurado en settings")

            client = BackupService._get_storage_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            raw_content = blob.download_as_string(timeout=600)
            
            # Normalizar contenido si no es bytes
            if isinstance(raw_content, bytes):
                content = raw_content.decode("utf-8", errors="replace")
            elif isinstance(raw_content, str):
                content = raw_content
            else:
                logger.warning(
                    f"Contenido descargado de GCS no es bytes ni string: {type(raw_content).__name__}, normalizando"
                )
                content = BackupService._coerce_dump_content(raw_content)
            
            if not isinstance(content, str):
                raise TypeError(
                    f"Contenido de GCS no se pudo convertir a string: {type(content).__name__}"
                )
            
            logger.info(f"Archivo descargado desde GCS: {blob_path}")
            return content
            
        except Exception as e:
            logger.error(f"Error descargando de GCS: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _media_backup_prefix_from_sql_blob_path(sql_blob_path: str) -> str:
        """
        Deriva el prefijo de media a partir de la ruta del SQL en GCS.
        Ejemplo: backups/global/backup_global_YYYYMMDD.sql -> backups/global/backup_global_YYYYMMDD_media
        """
        if not sql_blob_path:
            raise ValueError("sql_blob_path es requerido para derivar el prefijo de media")

        sql_blob_path = str(sql_blob_path).strip("/")
        sql_dir = sql_blob_path.rsplit("/", 1)[0] if "/" in sql_blob_path else ""
        sql_name = sql_blob_path.rsplit("/", 1)[-1]
        base_name = os.path.splitext(sql_name)[0]
        media_prefix = f"{sql_dir}/{base_name}_media" if sql_dir else f"{base_name}_media"
        return media_prefix.strip("/")

    @staticmethod
    def _upload_media_files_to_gcs(media_prefix: str) -> Dict[str, int]:
        """
        Sube todos los archivos de `MEDIA_ROOT` a GCS como blobs individuales.
        Mantiene la estructura relativa dentro del prefijo de media.
        """
        try:
            media_root = getattr(settings, "MEDIA_ROOT", None)
            if not media_root:
                raise ValueError("MEDIA_ROOT no está configurado en settings")

            media_root_path = Path(media_root)
            if not media_root_path.exists():
                logger.info("MEDIA_ROOT no existe, no hay archivos para subir")
                return {"files": 0, "bytes": 0}

            bucket_name = getattr(settings, "GCS_BUCKET_NAME", None)
            if not bucket_name:
                raise ValueError("GCS_BUCKET_NAME no configurado en settings")

            client = BackupService._get_storage_client()
            bucket = client.bucket(bucket_name)
            uploaded_files = 0
            uploaded_bytes = 0

            for file_path in media_root_path.rglob("*"):
                if not file_path.is_file():
                    continue

                relative_path = file_path.relative_to(media_root_path).as_posix()
                blob_name = f"{media_prefix.strip('/')}/{relative_path}".strip("/")
                blob = bucket.blob(blob_name)
                content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
                blob.upload_from_filename(str(file_path), content_type=content_type, timeout=600)
                uploaded_files += 1
                try:
                    uploaded_bytes += file_path.stat().st_size
                except Exception:
                    pass

            logger.info(
                f"Media subida a GCS: {uploaded_files} archivos en prefijo {media_prefix}"
            )
            return {"files": uploaded_files, "bytes": uploaded_bytes}
        except Exception:
            logger.exception("Error subiendo media a GCS")
            raise

    @staticmethod
    def _restore_media_files_from_gcs(media_prefix: str) -> int:
        """
        Descarga desde GCS todos los blobs bajo un prefijo de media y los escribe en MEDIA_ROOT.
        """
        try:
            if not media_prefix:
                logger.debug("No hay prefijo de media para restaurar")
                return 0

            media_root = getattr(settings, "MEDIA_ROOT", None)
            if not media_root:
                raise ValueError("MEDIA_ROOT no está configurado en settings")

            media_root_path = Path(media_root)
            media_root_path.mkdir(parents=True, exist_ok=True)

            bucket_name = getattr(settings, "GCS_BUCKET_NAME", None)
            if not bucket_name:
                raise ValueError("GCS_BUCKET_NAME no configurado en settings")

            client = BackupService._get_storage_client()
            prefix = media_prefix.strip("/") + "/"
            blobs = list(client.list_blobs(bucket_name, prefix=prefix))

            restored_files = 0
            for blob in blobs:
                if not blob.name or blob.name.endswith("/"):
                    continue

                relative_path = blob.name[len(prefix):].lstrip("/")
                if not relative_path:
                    continue

                local_path = media_root_path.joinpath(*relative_path.split("/"))
                local_path.parent.mkdir(parents=True, exist_ok=True)
                blob.download_to_filename(str(local_path), timeout=600)
                restored_files += 1

            logger.info(
                f"Media restaurada desde GCS: {restored_files} archivos en prefijo {media_prefix}"
            )
            return restored_files
        except Exception:
            logger.exception("Error restaurando media desde GCS por archivos")
            raise

    @staticmethod
    def _restore_legacy_media_zip_from_gcs(sql_blob_path: str) -> None:
        """
        Compatibilidad temporal para backups antiguos que guardaron media como ZIP.
        """
        legacy_media_blob = None
        if sql_blob_path and str(sql_blob_path).endswith(".sql"):
            legacy_media_blob = str(sql_blob_path).replace(".sql", "_media.zip")

        if not legacy_media_blob:
            return

        try:
            client = BackupService._get_storage_client()
            bucket_name = getattr(settings, "GCS_BUCKET_NAME", None)
            if not bucket_name:
                raise ValueError("GCS_BUCKET_NAME no configurado en settings")

            bucket = client.bucket(bucket_name)
            blob = bucket.blob(legacy_media_blob)
            if not blob.exists(client):
                logger.warning(f"No existe media legacy en GCS: {legacy_media_blob}")
                return

            tmp_dir = tempfile.mkdtemp(prefix="pethome_media_")
            tmp_zip = os.path.join(tmp_dir, "media.zip")
            blob.download_to_filename(tmp_zip, timeout=600)

            media_root = getattr(settings, "MEDIA_ROOT", None)
            if not media_root:
                raise ValueError("MEDIA_ROOT no está configurado en settings")

            with zipfile.ZipFile(tmp_zip, 'r') as zf:
                zf.extractall(media_root)

            logger.info(f"Media legacy restaurada desde GCS: {legacy_media_blob}")
        except Exception:
            logger.exception("Error restaurando media legacy desde GCS")
            raise

    @staticmethod
    def update_backup_config(
        veterinaria_id: int,
        frecuencia: str,
        dias_retención: int,
        usuario: Any,
        hora_ejecucion: Optional[int] = None,
        minuto_ejecucion: Optional[int] = None,
        dias_semana: Optional[list[int]] = None,
        request: Optional[Any] = None,
    ) -> Optional[BackupConfig]:
        """
        Actualiza la configuración de backups automáticos de una veterinaria.
        """
        try:
            config, created = BackupConfig.objects.get_or_create(
                veterinaria_id=veterinaria_id
            )
            
            old_frecuencia = config.frecuencia
            config.frecuencia = frecuencia
            config.dias_retención = dias_retención
            if hora_ejecucion is not None:
                config.hora_ejecucion = hora_ejecucion
            if minuto_ejecucion is not None:
                config.minuto_ejecucion = minuto_ejecucion
            if dias_semana is not None:
                config.dias_semana = dias_semana
            
            # Calcular próximo backup usando la configuración completa
            config.próximo_backup_programado = BackupService._calculate_next_backup_with_config(config)
            
            config.save()
            
            # Registrar en bitácora
            BitacoraService.registrar_evento(
                accion="BACKUP_CONFIG_ACTUALIZADA",
                descripcion=f"Configuración de backup actualizada: {old_frecuencia} → {frecuencia}",
                usuario=usuario,
                request=request,
                modulo="backups",
                entidad_tipo="BackupConfig",
                entidad_id=str(config.id_backup_config),
                resultado="EXITO",
                metadatos={
                    "veterinaria_id": veterinaria_id,
                    "frecuencia_anterior": old_frecuencia,
                    "frecuencia_nueva": frecuencia,
                    "días_retención": dias_retención,
                }
            )
            
            logger.info(f"Configuración de backup actualizada para veterinaria {veterinaria_id}")
            return config
            
        except Exception as e:
            logger.error(f"Error actualizando configuración de backup: {str(e)}")
            BitacoraService.registrar_evento(
                accion="BACKUP_CONFIG_ERROR",
                descripcion=f"Error al actualizar config: {str(e)}",
                usuario=usuario,
                request=request,
                modulo="backups",
                resultado="FALLO",
            )
            return None

    @staticmethod
    def _calculate_next_backup(frecuencia: str) -> datetime:
        """
        Calcula la fecha/hora del próximo backup según la frecuencia básica.
        Para configuraciones personalizadas, usar _calculate_next_backup_with_config().
        """
        now = datetime.now()
        
        if frecuencia == "DIARIO":
            return now + timedelta(days=1)
        elif frecuencia == "SEMANAL":
            return now + timedelta(weeks=1)
        elif frecuencia == "MENSUAL":
            return now + timedelta(days=30)
        else:  # PERSONALIZADO o desconocido
            return now + timedelta(weeks=1)  # Default a semanal

    @staticmethod
    def _calculate_next_backup_with_config(
        config: BackupConfig,
        reference_time: Optional[datetime] = None,
    ) -> datetime:
        """
        Calcula la fecha/hora del próximo backup considerando la configuración completa.
        Soporta horarios personalizados con días específicos.
        
        Args:
            config: Instancia de BackupConfig con todos los campos
            
        Returns:
            datetime con la próxima ejecución programada
        """
        from django.utils import timezone

        now = reference_time or timezone.now()
        if timezone.is_naive(now):
            now = timezone.make_aware(now, timezone.get_current_timezone())
        # Usar hora local definida en settings.TIME_ZONE para calcular la hora esperada por el usuario
        local_now = timezone.localtime(now)
        
        if config.frecuencia == "DIARIO":
            # Próximo día a la hora especificada (default 02:00)
            # Construir en horario local y convertir a UTC para almacenamiento
            candidate_local = local_now.replace(hour=config.hora_ejecucion, minute=config.minuto_ejecucion, second=0, microsecond=0)
            if candidate_local <= local_now:
                candidate_local = candidate_local + timedelta(days=1)
            return candidate_local.astimezone(dt_timezone.utc)
            
        elif config.frecuencia == "SEMANAL":
            # Próxima semana o mismo día si la hora no ha pasado
            candidate_local = local_now.replace(hour=config.hora_ejecucion, minute=config.minuto_ejecucion, second=0, microsecond=0)
            if candidate_local <= local_now:
                candidate_local = candidate_local + timedelta(weeks=1)
            return candidate_local.astimezone(dt_timezone.utc)
            
        elif config.frecuencia == "MENSUAL":
            # Próximo mes, mismo día, hora especificada
            if local_now.month == 12:
                next_time = local_now.replace(year=local_now.year + 1, month=1, day=local_now.day)
            else:
                next_time = local_now.replace(month=local_now.month + 1, day=local_now.day)
            next_time = next_time.replace(hour=config.hora_ejecucion, minute=config.minuto_ejecucion, second=0, microsecond=0)
            return next_time.astimezone(dt_timezone.utc)
            
        elif config.frecuencia == "PERSONALIZADO":
            # Encontrar próximo día que coincida con dias_semana
            normalized_days = BackupService._normalize_weekdays(config.dias_semana)

            if not normalized_days:
                logger.warning(f"BackupConfig {config.id_backup_config} tiene PERSONALIZADO pero sin días configurados")
                return now + timedelta(weeks=1)

            # Comenzar desde hoy a la hora configurada; permitir el mismo día si la hora no ha pasado
            candidate_local = local_now.replace(hour=config.hora_ejecucion, minute=config.minuto_ejecucion, second=0, microsecond=0)

            # Buscar el próximo día que esté en dias_semana (0=lunes, 6=domingo)
            max_attempts = 7
            for _ in range(max_attempts):
                weekday = candidate_local.weekday()  # 0-6 (lunes-domingo en Python)
                if weekday in normalized_days and candidate_local > local_now:
                    return candidate_local.astimezone(dt_timezone.utc)
                # avanzar un día y mantener la hora configurada
                candidate_local = (candidate_local + timedelta(days=1)).replace(hour=config.hora_ejecucion, minute=config.minuto_ejecucion, second=0, microsecond=0)

            # Si no encuentra en 7 días, usar el default
            logger.warning(f"No se encontró día válido en dias_semana para BackupConfig {config.id_backup_config}")
            return now + timedelta(weeks=1)
        
        else:
            # Default desconocido
            return now + timedelta(weeks=1)

    @staticmethod
    def _normalize_weekdays(days: Any) -> list[int]:
        """
        Normaliza dias_semana a una lista de enteros 0..6 (0=lunes).
        Tolera valores como strings numéricos en datos legacy.
        """
        if not days:
            return []

        normalized: list[int] = []
        for d in days:
            try:
                val = int(d)
            except (TypeError, ValueError):
                continue
            if 0 <= val <= 6 and val not in normalized:
                normalized.append(val)

        return sorted(normalized)

    @staticmethod
    def cleanup_old_backups(veterinaria_id: int, days_retention: int) -> int:
        """
        Borra backups más antiguos que días_retention.
        Retorna la cantidad de registros eliminados.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_retention)
            
            old_backups = BackupRestore.objects.filter(
                veterinaria_id=veterinaria_id,
                tipo="BACKUP",
                estado="EXITOSO",
                fecha_hora__lt=cutoff_date,
            )
            
            count = old_backups.count()
            
            # Opcional: eliminar de GCS también
            for backup in old_backups:
                try:
                    BackupService._delete_from_gcs(backup.ruta_archivo)
                except Exception as e:
                    logger.warning(f"No se pudo eliminar de GCS: {backup.ruta_archivo} - {str(e)}")
            
            old_backups.delete()
            logger.info(f"Eliminados {count} backups antiguos para veterinaria {veterinaria_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error limpiando backups antiguos: {str(e)}")
            return 0

    @staticmethod
    def _delete_from_gcs(blob_path: str) -> None:
        """
        Elimina un archivo de Google Cloud Storage.
        """
        try:
            bucket_name = getattr(settings, "GCS_BUCKET_NAME", None)
            if not bucket_name:
                raise ValueError("GCS_BUCKET_NAME no configurado en settings")

            client = BackupService._get_storage_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.delete(timeout=300)
            
            logger.info(f"Archivo eliminado de GCS: {blob_path}")
            
        except Exception as e:
            logger.error(f"Error eliminando de GCS: {str(e)}")
            raise

    @staticmethod
    def _get_storage_client():
        """
        Devuelve un cliente de Google Cloud Storage usando credenciales del entorno.
        """
        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError("google-cloud-storage no instalado. Ejecuta: pip install google-cloud-storage")

        project_id = getattr(settings, "GCS_PROJECT_ID", None) or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if project_id:
            return storage.Client(project=project_id)

        return storage.Client()

    @staticmethod
    def _resolve_postgres_executable(configured_path: str, executable_filename: str) -> str:
        """
        Resuelve la ruta del ejecutable de PostgreSQL.
        
        Estrategia de resolución (en orden):
        1. Ruta configurada en .env
        2. PATH del sistema
        3. Instalaciones típicas en C:\\Program Files\\PostgreSQL\\*\\bin
        """
        if configured_path:
            expanded_path = os.path.expandvars(configured_path)
            if os.path.isabs(expanded_path) and os.path.exists(expanded_path):
                return expanded_path
            found_in_path = which(expanded_path)
            if found_in_path:
                return found_in_path

        found_in_path = which(executable_filename)
        if found_in_path:
            return found_in_path

        windows_candidates = glob(r"C:\Program Files\PostgreSQL\*\bin\%s" % executable_filename)
        if windows_candidates:
            return windows_candidates[0]

        raise FileNotFoundError(
            f"No se encontró {executable_filename}. Configura PG_DUMP_PATH/PSQL_PATH con la ruta completa."
        )
