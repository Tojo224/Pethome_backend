from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraModulo, BitacoraResultado, BitacoraAccion
from ..selectors.clinica_selector import ConsultaClinicaSelector, RecetaSelector
from ..services.clinica_service import ClinicaService
from ..serializers import RecetaSerializer


class RecetaPorConsultaView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_RECETAS"

    @extend_schema(
        tags=["Clinica"],
        responses={200: RecetaSerializer, 404: OpenApiResponse(description="No encontrado.")},
        description="Obtiene la receta asociada a una consulta clínica."
    )
    def get(self, request, id_consulta_clinica):
        vet_id = self.get_tenant_id()
        # Validar acceso a la consulta
        consulta = ConsultaClinicaSelector.get_consulta_detail(id_consulta_clinica, vet_id)
        if not consulta:
            return Response({"error": "Consulta no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)

        receta = RecetaSelector.get_recetas_by_consulta(id_consulta_clinica, vet_id).first()
        if not receta:
             return Response({"error": "No hay receta para esta consulta."}, status=status.HTTP_404_NOT_FOUND)
             
        serializer = RecetaSerializer(receta, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        tags=["Clinica"],
        request=RecetaSerializer,
        responses={201: RecetaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
        description="Emite una receta para una consulta clínica."
    )
    def post(self, request, id_consulta_clinica):
        vet_id = self.get_tenant_id()
        # Validar acceso a la consulta
        consulta = ConsultaClinicaSelector.get_consulta_detail(id_consulta_clinica, vet_id)
        if not consulta:
            return Response({"error": "Consulta no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(consulta, "receta"):
            return Response({"error": "La consulta ya tiene una receta."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RecetaSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            receta = ClinicaService.crear_receta(
                consulta_id=id_consulta_clinica,
                indicaciones=serializer.validated_data.get("indicaciones"),
                observacion=serializer.validated_data.get("observacion")
            )
            
            self.registrar_bitacora(
                accion=BitacoraAccion.RECETA_REGISTRADA,
                descripcion=f"Receta #{receta.pk} emitida para la consulta #{id_consulta_clinica}.",
                modulo=BitacoraModulo.CLINICA,
                entidad_id=receta.pk,
                resultado=BitacoraResultado.EXITO
            )
            return Response(RecetaSerializer(receta).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecetaDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_RECETAS"

    @extend_schema(tags=["Clinica"], responses={200: RecetaSerializer})
    def get(self, request, id_receta):
        vet_id = self.get_tenant_id()
        receta = RecetaSelector.get_recetas_by_consulta(None, vet_id).filter(pk=id_receta).first()
        
        if not receta:
            return Response({"error": "Receta no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = RecetaSerializer(receta)
        return Response(serializer.data)
