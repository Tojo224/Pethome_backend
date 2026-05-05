from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraModulo, BitacoraResultado, BitacoraAccion
from ..selectors.servicios_selector import CitaSelector
from ..serializers.citas_serializer import CitaSerializer

class DisponibilidadAgendaView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_CITAS"

    @extend_schema(
        tags=["Agenda"],
        operation_id="agenda_disponibilidad",
        parameters=[
            OpenApiParameter("fecha", type=str, description="Fecha a consultar (YYYY-MM-DD)", required=True),
        ],
        responses={200: CitaSerializer(many=True)},
    )
    def get(self, request):
        fecha = request.query_params.get("fecha")
        if not fecha:
            return Response({"error": "La fecha es requerida."}, status=status.HTTP_400_BAD_REQUEST)

        vet_id = self.get_tenant_id()
        
        # 1. Obtener citas ocupadas para ese día
        citas_ocupadas = CitaSelector.get_citas_by_fecha(vet_id, fecha)
        serializer = CitaSerializer(citas_ocupadas, many=True)

        # 2. Registrar en bitácora
        self.registrar_bitacora(
            accion=BitacoraAccion.DISPONIBILIDAD_CONSULTADA,
            descripcion=f"Consulta de horarios disponibles para la fecha {fecha}.",
            modulo=BitacoraModulo.AGENDA_DISPONIBILIDAD,
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "fecha_programada": fecha,
                "citas_ocupadas_count": citas_ocupadas.count()
            }
        )

        # Retornamos las citas ocupadas. El frontend se encargará de mostrar los huecos libres
        # o podemos implementar una lógica de "slots" si el negocio tiene horarios fijos.
        return Response({
            "fecha": fecha,
            "citas_ocupadas": serializer.data,
            "mensaje": "Se muestran los horarios ocupados. Los espacios restantes están disponibles."
        })

class ValidarConflictoView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_CITAS"

    @extend_schema(
        tags=["Agenda"],
        parameters=[
            OpenApiParameter("fecha", type=str, required=True),
            OpenApiParameter("hora_inicio", type=str, required=True),
            OpenApiParameter("hora_fin", type=str, required=True),
        ],
    )
    def get(self, request):
        fecha = request.query_params.get("fecha")
        h_ini = request.query_params.get("hora_inicio")
        h_fin = request.query_params.get("hora_fin")

        if not all([fecha, h_ini, h_fin]):
            return Response({"error": "Faltan parámetros."}, status=status.HTTP_400_BAD_REQUEST)

        conflicto = CitaSelector.verificar_conflicto_horario(self.get_tenant_id(), fecha, h_ini, h_fin)
        
        if conflicto:
            self.registrar_bitacora(
                accion=BitacoraAccion.CONFLICTO_HORARIO_DETECTADO,
                descripcion=f"Conflicto de horario detectado para el {fecha} entre {h_ini} y {h_fin}.",
                modulo=BitacoraModulo.AGENDA_DISPONIBILIDAD,
                resultado=BitacoraResultado.FALLO,
                metadatos={"fecha": fecha, "hora_inicio": h_ini, "hora_fin": h_fin}
            )

        return Response({
            "disponible": not conflicto,
            "mensaje": "Horario disponible" if not conflicto else "Horario ocupado"
        })
