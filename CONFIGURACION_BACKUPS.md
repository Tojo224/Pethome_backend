# ==============================================================================
# CONFIGURACIÓN DE BACKUPS - Google Cloud Storage
# ==============================================================================
#
# Esta es una referencia de configuración necesaria para que el sistema de
# backups funcione correctamente. Agregar lo siguiente a tu settings.py:
#
# ==============================================================================

# 1. BUCKET DE GOOGLE CLOUD STORAGE
# Reemplaza 'tu-bucket-name' con el nombre real de tu bucket en GCS
GCS_BUCKET_NAME = "tu-bucket-name"  # Ejemplo: "pethome-backups-production"

# 2. AUTENTICACIÓN DE GCS
# Opción A: Usando credenciales JSON (para desarrollo/testing)
# Establecer la variable de entorno GOOGLE_APPLICATION_CREDENTIALS
# export GOOGLE_APPLICATION_CREDENTIALS="/ruta/a/tu/credenciales.json"

# Opción B: Usando Application Default Credentials (en Google Cloud Run/Compute Engine)
# Las credenciales se autentican automáticamente desde el ambiente

# 3. CONFIGURACIÓN DEL SCHEDULER
# El scheduler debe ejecutarse periódicamente para procesar backups automáticos.
# 
# OPCIÓN A: APScheduler (simple, sin dependencias externas)
# Requiere:
#   pip install apscheduler
#
# OPCIÓN B: Celery + Redis (más robusto para producción)
# Requiere:
#   pip install celery redis
#

# 4. VARIABLES DE ENTORNO RECOMENDADAS
# Agregar a tu .env:
#
# DATABASE_URL=postgresql://user:password@localhost:5432/pethome
# GCS_BUCKET_NAME=pethome-backups-production
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
# BACKUP_RETENTION_DAYS=30
#

# ==============================================================================
# INSTALACIÓN DE DEPENDENCIAS
# ==============================================================================
#
# Agregar a requirements.txt:
#
#   google-cloud-storage>=2.10.0
#   apscheduler>=3.10.0  (si usas APScheduler)
#   celery>=5.3.0        (si usas Celery)
#   redis>=4.5.0         (si usas Celery + Redis)
#
# Luego ejecutar:
#   pip install -r requirements.txt

# ==============================================================================
# CREACIÓN DE BUCKET EN GCS
# ==============================================================================
#
# gcloud storage buckets create gs://pethome-backups-production
# gcloud storage buckets update gs://pethome-backups-production \
#   --lifecycle-add-delete-age=30d
#

# ==============================================================================
# PERMISOS NECESARIOS EN DJANGO
# ==============================================================================
#
# El componente de permiso 'SEG_BACKUPS' debe estar registrado en la BD
# Se puede crear manualmente o mediante:
#
# from apps.AutenticacionySeguridad.models import ComponenteSistema
# ComponenteSistema.objects.get_or_create(
#     nombre="SEG_BACKUPS",
#     defaults={"descripcion": "Gestión de copias de seguridad"}
# )
#
