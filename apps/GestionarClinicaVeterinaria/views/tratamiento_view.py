from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraModulo, BitacoraResultado, BitacoraAccion
from ..selectors.clinica_selector import ConsultaClinicaSelector, TratamientoSelector
from ..services.clinica_service import ClinicaService
from ..serializers import TratamientoSerializer


class TratamientoListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_TRATAMIENTOS"

    @extend_schema(
        tags=["Clinica"],
        responses={200: TratamientoSerializer(many=True)},
        description="Lista los tratamientos asociados a una consulta clínica del tenant."
    )
    def get(self, request, id_consulta_clinica):
        vet_id = self.get_tenant_id()
        # Validar acceso a la consulta
        consulta = ConsultaClinicaSelector.get_consulta_detail(id_consulta_clinica, vet_id)
        if not consulta:
            return Response({"error": "Consulta no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)

        tratamientos = TratamientoSelector.get_tratamientos_by_consulta(id_consulta_clinica, vet_id)
        serializer = TratamientoSerializer(tratamientos, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Clinica"],
        request=TratamientoSerializer,
        responses={201: TratamientoSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
        description="Registra un nuevo tratamiento para una consulta clínica."
    )
    def post(self, request, id_consulta_clinica):
        vet_id = self.get_tenant_id()
        # Validar acceso a la consulta
        consulta = ConsultaClinicaSelector.get_consulta_detail(id_consulta_clinica, vet_id)
        if not consulta:
            return Response({"error": "Consulta no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TratamientoSerializer(data=request.data)
        if serializer.is_valid():
            tratamiento = ClinicaService.agregar_tratamiento(
                consulta_id=id_consulta_clinica,
                tipo=serializer.validated_data.get("tipo"),
                descripcion=serializer.validated_data.get("descripcion"),
                fecha_ini=serializer.validated_data.get("fecha_ini"),
                fecha_fin=serializer.validated_data.get("fecha_fin"),
                observacion=serializer.validated_data.get("observacion")
            )
            
            self.registrar_bitacora(
                accion=BitacoraAccion.TRATAMIENTO_REGISTRADO,
                descripcion=f"Tratamiento registrado para la consulta #{id_consulta_clinica}.",
                modulo=BitacoraModulo.CLINICA,
                entidad_id=tratamiento.pk,
                resultado=BitacoraResultado.EXITO
            )
            return Response(TratamientoSerializer(tratamiento).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TratamientoDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_TRATAMIENTOS"

    @extend_schema(tags=["Clinica"], responses={200: TratamientoSerializer})
    def get(self, request, id_tratamiento):
        vet_id = self.get_tenant_id()
        tratamiento = TratamientoSelector.get_tratamientos_by_consulta(None, vet_id).filter(pk=id_tratamiento).first()
        
        if not tratamiento:
            return Response({"error": "Tratamiento no encontrado o sin acceso."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = TratamientoSerializer(tratamiento)
        return Response(serializer.data)
