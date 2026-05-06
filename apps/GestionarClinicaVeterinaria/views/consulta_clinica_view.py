from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraModulo, BitacoraResultado, BitacoraAccion
from apps.GestionServiciosyReserva.selectors.servicios_selector import CitaSelector
from ..selectors.clinica_selector import ConsultaClinicaSelector, HistorialClinicoSelector
from ..services.clinica_service import ClinicaService
from ..serializers import ConsultaClinicaSerializer


class ConsultaClinicaListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CONSULTAS"

    @extend_schema(
        tags=["Clinica"],
        responses={200: ConsultaClinicaSerializer(many=True)},
        description="Lista las consultas de un historial clínico específico del tenant."
    )
    def get(self, request, id_historial_clinico):
        vet_id = self.get_tenant_id()
        
        # Validar acceso al historial (pertenencia al tenant)
        historial = HistorialClinicoSelector.get_historial_by_mascota(id_historial_clinico, vet_id) # Usamos mascota_id como proxy si aplica
        if not historial:
             # Intentar por ID directo si falla
             historial = HistorialClinicoSelector.get_historiales_by_tenant(vet_id).filter(pk=id_historial_clinico).first()
        
        if not historial:
            return Response({"error": "Historial no encontrado o sin acceso."}, status=status.HTTP_404_NOT_FOUND)

        consultas = ConsultaClinicaSelector.get_consultas_by_historial(historial.pk, vet_id)
        serializer = ConsultaClinicaSerializer(consultas, many=True)
        
        self.registrar_bitacora(
            accion=BitacoraAccion.CONSULTA_CLINICA_CONSULTADA,
            descripcion=f"Consultas del historial #{historial.pk} visualizadas.",
            modulo=BitacoraModulo.CLINICA,
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": consultas.count()}
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["Clinica"],
        request=ConsultaClinicaSerializer,
        responses={201: ConsultaClinicaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
        description="Registra una nueva consulta clínica validando mascota y cita del tenant."
    )
    def post(self, request, id_historial_clinico):
        vet_id = self.get_tenant_id()
        serializer = ConsultaClinicaSerializer(data=request.data)
        
        if not serializer.is_valid():
             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 1. Validar que la mascota pertenece al tenant (Regla SaaS #1)
        # Asumimos que id_historial_clinico en la URL puede ser el ID de la mascota por facilidad de API
        # o validamos el historial directo.
        historial = HistorialClinicoSelector.get_historiales_by_tenant(vet_id).filter(pk=id_historial_clinico).first()
        if not historial:
             return Response({"error": "Historial clínico no válido para este tenant."}, status=status.HTTP_403_FORBIDDEN)

        # 2. Validar Cita si se proporciona (Regla SaaS #8)
        cita_id = request.data.get("cita")
        if cita_id:
            cita = CitaSelector.get_cita_detail(cita_id, vet_id)
            if not cita:
                return Response({"error": "La cita proporcionada no pertenece a su veterinaria."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            consulta = ClinicaService.registrar_consulta(
                veterinaria_id=vet_id,
                mascota_id=historial.mascota_id,
                veterinario_id=request.user.id_usuario,
                motivo=serializer.validated_data.get("motivo_consulta"),
                diagnostico=serializer.validated_data.get("diagnostico"),
                observaciones=serializer.validated_data.get("observaciones"),
                cita_id=cita_id,
                peso=serializer.validated_data.get("peso"),
                temperatura=serializer.validated_data.get("temperatura"),
                f_cardiaca=serializer.validated_data.get("frecuencia_cardiaca"),
                f_respiratoria=serializer.validated_data.get("frecuencia_respiratoria")
            )

            self.registrar_bitacora(
                accion=BitacoraAccion.CONSULTA_CLINICA_CREADA,
                descripcion=f"Consulta clínica #{consulta.pk} registrada para '{historial.mascota.nombre}'.",
                modulo=BitacoraModulo.CLINICA,
                entidad_id=consulta.pk,
                resultado=BitacoraResultado.EXITO
            )
            return Response(ConsultaClinicaSerializer(consulta).data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.CONSULTA_CLINICA_CREADA,
                descripcion="Falló el registro de la consulta clínica.",
                modulo=BitacoraModulo.CLINICA,
                resultado=BitacoraResultado.FALLO,
                metadatos={"error": str(e)}
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ConsultaClinicaDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CONSULTAS"

    @extend_schema(tags=["Clinica"], responses={200: ConsultaClinicaSerializer})
    def get(self, request, id_consulta_clinica):
        vet_id = self.get_tenant_id()
        consulta = ConsultaClinicaSelector.get_consulta_detail(id_consulta_clinica, vet_id)
        
        if not consulta:
            return Response({"error": "Consulta no encontrada o sin acceso."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = ConsultaClinicaSerializer(consulta)
        return Response(serializer.data)
