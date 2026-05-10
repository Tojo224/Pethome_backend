from datetime import datetime, time, timedelta

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)
from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import (
    HasComponentPermission,
)

from ..selectors.servicios_selector import CitaSelector, ServicioSelector
from ..serializers.citas_serializer import CitaSerializer


class DisponibilidadAgendaView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_CITAS"

    @extend_schema(
        tags=["Agenda"],
        operation_id="agenda_disponibilidad",
        parameters=[
            OpenApiParameter(
                "fecha",
                type=str,
                description="Fecha a consultar (YYYY-MM-DD)",
                required=True,
            ),
            OpenApiParameter(
                "servicio",
                type=int,
                description="ID del servicio para calcular la duracion",
            ),
            OpenApiParameter(
                "modalidad",
                type=str,
                description="Modalidad solicitada",
            ),
        ],
        responses={200: CitaSerializer(many=True)},
    )
    def get(self, request):
        fecha = request.query_params.get("fecha")
        if not fecha:
            return Response(
                {"error": "La fecha es requerida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vet_id = self.get_tenant_id()
        servicio_id = request.query_params.get("servicio") or request.query_params.get(
            "service_id"
        )
        modalidad = (request.query_params.get("modalidad") or "").strip().upper()

        duracion_minutos = 30
        if servicio_id:
            servicio = ServicioSelector.get_servicio_detail(servicio_id, vet_id)
            if servicio and getattr(servicio, "duracion_estimada", None):
                duracion_minutos = int(servicio.duracion_estimada)

        citas_ocupadas = CitaSelector.get_citas_by_fecha(vet_id, fecha)
        serializer = CitaSerializer(citas_ocupadas, many=True)

        hora_apertura = 8
        hora_cierre = 18
        slot_minutos = 30

        slots_disponibles = []
        current_dt = datetime.combine(
            datetime.strptime(fecha, "%Y-%m-%d").date(),
            time(hora_apertura, 0),
        )
        end_dt = datetime.combine(current_dt.date(), time(hora_cierre, 0))
        now = timezone.localtime()
        now_naive = now.replace(tzinfo=None)

        while current_dt < end_dt:
            slot_fin_dt = current_dt + timedelta(minutes=duracion_minutos)
            if slot_fin_dt > end_dt:
                break

            slot_inicio = current_dt.time()
            slot_fin = slot_fin_dt.time()

            if current_dt.date() < now.date() or (
                current_dt.date() == now.date() and current_dt <= now_naive
            ):
                current_dt += timedelta(minutes=slot_minutos)
                continue

            esta_ocupado = CitaSelector.verificar_conflicto_horario(
                vet_id,
                current_dt.date(),
                slot_inicio,
                slot_fin,
            )

            if not esta_ocupado:
                slots_disponibles.append(
                    {
                        "inicio": slot_inicio.strftime("%H:%M"),
                        "fin": slot_fin.strftime("%H:%M"),
                    }
                )

            current_dt += timedelta(minutes=slot_minutos)

        self.registrar_bitacora(
            accion=BitacoraAccion.DISPONIBILIDAD_CONSULTADA,
            descripcion=f"Consulta de horarios disponibles para la fecha {fecha}.",
            modulo=BitacoraModulo.AGENDA_DISPONIBILIDAD,
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "fecha_programada": fecha,
                "servicio": servicio_id,
                "modalidad": modalidad or None,
                "duracion_minutos": duracion_minutos,
                "citas_ocupadas_count": citas_ocupadas.count(),
                "slots_disponibles_count": len(slots_disponibles),
            },
        )

        return Response(
            {
                "fecha": fecha,
                "servicio": servicio_id,
                "duracion_minutos": duracion_minutos,
                "citas_ocupadas": serializer.data,
                "horarios_disponibles": slots_disponibles,
                "mensaje": "Se muestran horarios ocupados y slots disponibles.",
            }
        )


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
            return Response(
                {"error": "Faltan parámetros."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conflicto = CitaSelector.verificar_conflicto_horario(
            self.get_tenant_id(),
            fecha,
            h_ini,
            h_fin,
        )

        if conflicto:
            self.registrar_bitacora(
                accion=BitacoraAccion.CONFLICTO_HORARIO_DETECTADO,
                descripcion=(
                    f"Conflicto de horario detectado para el {fecha} entre "
                    f"{h_ini} y {h_fin}."
                ),
                modulo=BitacoraModulo.AGENDA_DISPONIBILIDAD,
                resultado=BitacoraResultado.FALLO,
                metadatos={
                    "fecha": fecha,
                    "hora_inicio": h_ini,
                    "hora_fin": h_fin,
                },
            )

        return Response(
            {
                "disponible": not conflicto,
                "mensaje": "Horario disponible" if not conflicto else "Horario ocupado",
            }
        )
