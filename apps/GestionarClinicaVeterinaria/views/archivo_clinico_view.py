from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraModulo, BitacoraResultado, BitacoraAccion
from ..selectors.clinica_selector import ConsultaClinicaSelector
from ..services.clinica_service import ClinicaService
from ..serializers.archivo_clinico_serializer import ArchivoClinicoSerializer


class ArchivoClinicoCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_ARCHIVOS"
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Clinica"],
        request=ArchivoClinicoSerializer,
        responses={201: ArchivoClinicoSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
        description="Adjunta un archivo clínico a una consulta específica del tenant."
    )
    def post(self, request, id_consulta_clinica):
        vet_id = self.get_tenant_id()
        # Validar acceso a la consulta
        consulta = ConsultaClinicaSelector.get_consulta_detail(id_consulta_clinica, vet_id)
        if not consulta:
            return Response({"error": "Consulta no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ArchivoClinicoSerializer(data=request.data)
        if serializer.is_valid():
            archivo = ClinicaService.adjuntar_archivo(
                consulta_id=id_consulta_clinica,
                nombre=serializer.validated_data.get("nombre_archivo"),
                archivo=serializer.validated_data.get("archivo"),
                tipo_archivo=serializer.validated_data.get("tipo_archivo")
            )
            
            self.registrar_bitacora(
                accion=BitacoraAccion.ARCHIVO_CLINICO_ADJUNTADO,
                descripcion=f"Archivo '{archivo.nombre_archivo}' adjuntado a la consulta #{id_consulta_clinica}.",
                modulo=BitacoraModulo.CLINICA,
                entidad_id=archivo.pk,
                resultado=BitacoraResultado.EXITO
            )
            return Response(ArchivoClinicoSerializer(archivo).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ArchivoClinicoUpdateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_ARCHIVOS"
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=["Clinica"], responses={200: ArchivoClinicoSerializer})
    def get(self, request, id_archivo_clinico):
        vet_id = self.get_tenant_id()
        archivo = ConsultaClinicaSelector.get_consulta_detail(None, vet_id).archivos_clinicos.filter(pk=id_archivo_clinico).first() # Dummy selector call or direct query
        # Correct way using direct query since we don't have a specific selector for files yet
        from ..models.archivo_clinico import ArchivoClinico
        archivo = ArchivoClinico.objects.filter(pk=id_archivo_clinico, consulta_clinica__veterinaria_id=vet_id).first()
        
        if not archivo:
            return Response({"error": "Archivo no encontrado o sin acceso."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = ArchivoClinicoSerializer(archivo)
        return Response(serializer.data)
