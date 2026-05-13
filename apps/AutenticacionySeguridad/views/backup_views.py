import logging
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from ..models.backup_restore import BackupRestore
from ..models.backup_config import BackupConfig
from ..serializers.backup_serializers import BackupRestoreSerializer, BackupConfigSerializer
from ..filters.backup_filters import BackupRestoreFilter
from ..permissions.tenant_rbac import HasComponentPermission
from ..services.backup_service import BackupService
from ..services.bitacora_register_service import BitacoraService
from ..mixins.tenant_mixins import TenantViewMixin

logger = logging.getLogger(__name__)


class BackupPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class BackupRestoreViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para listar backups y restauraciones.
    Solo lectura para el historial.
    """
    serializer_class = BackupRestoreSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_BACKUPS"
    pagination_class = BackupPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = BackupRestoreFilter
    ordering_fields = ["fecha_hora", "id_backup_restore"]
    ordering = ["-fecha_hora"]

    def get_queryset(self):
        """Retorna backups/restores de la veterinaria actual del usuario."""
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return BackupRestore.objects.filter(veterinaria_id=tenant.id).select_related(
                "usuario", "veterinaria"
            )
        return BackupRestore.objects.none()

    @extend_schema(
        tags=["Backups"],
        parameters=[
            OpenApiParameter("tipo", OpenApiTypes.STR, required=False),
            OpenApiParameter("estado", OpenApiTypes.STR, required=False),
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False),
        ],
        responses={200: BackupRestoreSerializer},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class BackupCreateView(TenantViewMixin, generics.CreateAPIView):
    """
    Endpoint para crear un backup manual.
    POST /backups/create/
    """
    serializer_class = BackupRestoreSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_BACKUPS"

    @extend_schema(
        tags=["Backups"],
        request=BackupRestoreSerializer,
        responses={201: BackupRestoreSerializer},
    )
    def post(self, request, *args, **kwargs):
        """Crea un backup manual de la BD."""
        try:
            tenant = getattr(request, "tenant", None)
            if not tenant:
                return Response(
                    {"error": "Tenant no encontrado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            motivo = request.data.get("motivo", "Backup manual")

            # Llamar servicio de backup
            backup = BackupService.create_backup(
                veterinaria_id=tenant.id,
                usuario=request.user,
                request=request,
                motivo=motivo,
            )

            if backup:
                serializer = self.get_serializer(backup)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"error": "No se pudo crear el backup"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except Exception as e:
            logger.error(f"Error en BackupCreateView: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BackupRestoreView(TenantViewMixin, generics.GenericAPIView):
    """
    Endpoint para restaurar desde un backup seleccionado.
    POST /backups/{backup_id}/restore/
    """
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_BACKUPS"
    serializer_class = BackupRestoreSerializer

    @extend_schema(
        tags=["Backups"],
        request=BackupRestoreSerializer,
        responses={200: {"type": "object", "properties": {"success": {"type": "boolean"}}}},
    )
    def post(self, request, backup_id, *args, **kwargs):
        """Restaura la BD desde un backup específico."""
        try:
            tenant = getattr(request, "tenant", None)
            if not tenant and not getattr(request.user, "is_superuser", False):
                return Response(
                    {"error": "Tenant no encontrado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            motivo = request.data.get("motivo", "Restauración manual")
            es_superuser = getattr(request.user, "is_superuser", False)
            scope = str(request.data.get("scope", "TENANT")).upper()

            if scope == "GLOBAL" and not es_superuser:
                return Response(
                    {"error": "Solo un superuser puede solicitar restauración global"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Validar alcance según rol
            if es_superuser:
                backup = BackupRestore.objects.get(
                    id_backup_restore=backup_id,
                    tipo="BACKUP",
                )
            else:
                backup = BackupRestore.objects.get(
                    id_backup_restore=backup_id,
                    veterinaria_id=tenant.id,
                    tipo="BACKUP",
                )

            # Llamar servicio de restore
            success = BackupService.restore_backup(
                backup_id=backup_id,
                usuario=request.user,
                request=request,
                motivo=motivo,
                scope=scope,
            )

            if success:
                return Response(
                    {"success": True, "message": "Restauración completada exitosamente"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"success": False, "error": "No se pudo restaurar el backup"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except BackupRestore.DoesNotExist:
            return Response(
                {"error": "Backup no encontrado o no pertenece a tu veterinaria"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error en BackupRestoreView: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BackupConfigRetrieveUpdateView(TenantViewMixin, generics.RetrieveUpdateAPIView):
    """
    Endpoint para obtener y actualizar la configuración de backups.
    GET  /backups/config/
    PUT  /backups/config/
    """
    serializer_class = BackupConfigSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_BACKUPS"

    def get_object(self):
        """Retorna la configuración de backup de la veterinaria actual."""
        tenant = getattr(self.request, "tenant", None)
        if not tenant:
            raise Exception("Tenant no encontrado")

        config, created = BackupConfig.objects.get_or_create(
            veterinaria_id=tenant.id
        )
        return config

    @extend_schema(
        tags=["Backups"],
        responses={200: BackupConfigSerializer},
    )
    def get(self, request, *args, **kwargs):
        """Obtiene la configuración de backups automáticos."""
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Backups"],
        request=BackupConfigSerializer,
        responses={200: BackupConfigSerializer},
    )
    def put(self, request, *args, **kwargs):
        """Actualiza la configuración de backups automáticos."""
        try:
            config = self.get_object()
            serializer = self.get_serializer(config, data=request.data, partial=True)
            
            if serializer.is_valid():
                frecuencia = serializer.validated_data.get("frecuencia", config.frecuencia)
                dias_retención = serializer.validated_data.get("dias_retención", config.dias_retención)
                hora_ejecucion = serializer.validated_data.get("hora_ejecucion", config.hora_ejecucion)
                minuto_ejecucion = serializer.validated_data.get("minuto_ejecucion", config.minuto_ejecucion)
                dias_semana = serializer.validated_data.get("dias_semana", config.dias_semana)
                
                # Usar el servicio para actualizar
                updated_config = BackupService.update_backup_config(
                    veterinaria_id=config.veterinaria.id_veterinaria,
                    frecuencia=frecuencia,
                    dias_retención=dias_retención,
                    hora_ejecucion=hora_ejecucion,
                    minuto_ejecucion=minuto_ejecucion,
                    dias_semana=dias_semana,
                    usuario=request.user,
                    request=request,
                )
                
                if updated_config:
                    serializer = self.get_serializer(updated_config)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"error": "No se pudo actualizar la configuración"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error en BackupConfigRetrieveUpdateView: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        tags=["Backups"],
        request=BackupConfigSerializer,
        responses={200: BackupConfigSerializer},
    )
    def patch(self, request, *args, **kwargs):
        """Actualiza parcialmente la configuración de backups."""
        try:
            config = self.get_object()
            serializer = self.get_serializer(config, data=request.data, partial=True)
            
            if serializer.is_valid():
                frecuencia = serializer.validated_data.get("frecuencia", config.frecuencia)
                dias_retención = serializer.validated_data.get("dias_retención", config.dias_retención)
                hora_ejecucion = serializer.validated_data.get("hora_ejecucion", config.hora_ejecucion)
                minuto_ejecucion = serializer.validated_data.get("minuto_ejecucion", config.minuto_ejecucion)
                dias_semana = serializer.validated_data.get("dias_semana", config.dias_semana)
                
                updated_config = BackupService.update_backup_config(
                    veterinaria_id=config.veterinaria.id_veterinaria,
                    frecuencia=frecuencia,
                    dias_retención=dias_retención,
                    hora_ejecucion=hora_ejecucion,
                    minuto_ejecucion=minuto_ejecucion,
                    dias_semana=dias_semana,
                    usuario=request.user,
                    request=request,
                )
                
                if updated_config:
                    serializer = self.get_serializer(updated_config)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"error": "No se pudo actualizar la configuración"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error en PATCH BackupConfigRetrieveUpdateView: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
