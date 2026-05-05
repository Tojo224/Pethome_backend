from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraModulo, BitacoraResultado, BitacoraAccion
from ..selectors.clinica_selector import ConsultaClinicaSelector, VacunaSelector
from ..services.clinica_service import ClinicaService
from ..serializers import VacunaAplicadaSerializer


class VacunaAplicadaListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_VACUNAS"

    @extend_schema(
        tags=["Clinica"],
        responses={200: VacunaAplicadaSerializer(many=True)},
        description="Lista las vacunas aplicadas en una consulta clínica específica."
    )
    def get(self, request, id_consulta_clinica):
        vet_id = self.get_tenant_id()
        # Validar acceso a la consulta
        consulta = ConsultaClinicaSelector.get_consulta_detail(id_consulta_clinica, vet_id)
        if not consulta:
            return Response({"error": "Consulta no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)

        vacunas = VacunaSelector.get_vacunas_by_mascota(None, vet_id).filter(consulta_clinica_id=id_consulta_clinica)
        serializer = VacunaAplicadaSerializer(vacunas, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Clinica"],
        request=VacunaAplicadaSerializer,
        responses={201: VacunaAplicadaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
        description="Registra una nueva vacuna aplicada para una consulta clínica."
    )
    def post(self, request, id_consulta_clinica):
        vet_id = self.get_tenant_id()
        # Validar acceso a la consulta
        consulta = ConsultaClinicaSelector.get_consulta_detail(id_consulta_clinica, vet_id)
        if not consulta:
            return Response({"error": "Consulta no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)

        serializer = VacunaAplicadaSerializer(data=request.data)
        if serializer.is_valid():
            vacuna = ClinicaService.registrar_vacuna(
                consulta_id=id_consulta_clinica,
                nombre_vacuna=serializer.validated_data.get("nombre_vacuna"),
                dosis=serializer.validated_data.get("dosis"),
                fecha_aplicada=serializer.validated_data.get("fecha_aplicada"),
                fecha_proxima=serializer.validated_data.get("fecha_proxima"),
                observacion=serializer.validated_data.get("observacion"),
                lote=serializer.validated_data.get("lote"),
                fabricante=serializer.validated_data.get("fabricante")
            )
            
            self.registrar_bitacora(
                accion=BitacoraAccion.VACUNA_REGISTRADA,
                descripcion=f"Vacuna '{vacuna.nombre_vacuna}' registrada para la consulta #{id_consulta_clinica}.",
                modulo=BitacoraModulo.CLINICA,
                entidad_id=vacuna.pk,
                resultado=BitacoraResultado.EXITO
            )
            return Response(VacunaAplicadaSerializer(vacuna).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VacunaAplicadaDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_VACUNAS"

    @extend_schema(tags=["Clinica"], responses={200: VacunaAplicadaSerializer})
    def get(self, request, id_vacuna_aplicada):
        vet_id = self.get_tenant_id()
        vacuna = VacunaSelector.get_vacunas_by_mascota(None, vet_id).filter(pk=id_vacuna_aplicada).first()
        
        if not vacuna:
            return Response({"error": "Vacuna no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = VacunaAplicadaSerializer(vacuna)
        return Response(serializer.data)
