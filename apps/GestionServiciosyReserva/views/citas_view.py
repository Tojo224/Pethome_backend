from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)
from rest_framework.permissions import IsAuthenticated

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from ..selectors.servicios_selector import CitaSelector
from ..services.citas_service import CitaService
from ..serializers.citas_serializer import (
    CitaEstadoUpdateSerializer,
    CitaSerializer,
)





class CitaListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_CITAS"

    def get_queryset(self, request):
        return CitaSelector.get_citas_by_tenant(
            veterinaria_id=self.get_tenant_id(),
            user=request.user
        ).order_by("-id_cita")

    @extend_schema(
        tags=["Citas"],
        operation_id="gestion_servicios_citas_list",
        responses={200: CitaSerializer},
    )
    def get(self, request):
        citas = self.get_queryset(request)
        serializer = CitaSerializer(citas, many=True)

        self.registrar_bitacora(
            accion=BitacoraAccion.CITA_CONSULTADA,
            descripcion="Listado de citas consultado.",
            modulo=BitacoraModulo.CITAS,
            metadatos={"total": citas.count()},
        )

        return Response(serializer.data)

    @extend_schema(
        tags=["Citas"],
        request=CitaSerializer,
        responses={201: CitaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def post(self, request):
        serializer = CitaSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            cita = CitaService.crear_cita(
                veterinaria_id=self.get_tenant_id(),
                usuario_id=request.user.id_usuario,
                mascota_id=serializer.validated_data.get("mascota").pk,
                servicio_id=serializer.validated_data.get("servicio").pk,
                precio_servicio_id=serializer.validated_data.get("precio_servicio").pk,
                fecha_programada=serializer.validated_data.get("fecha_programada"),
                hora_inicio=serializer.validated_data.get("hora_inicio"),
                hora_fin=serializer.validated_data.get("hora_fin"),
                modalidad=serializer.validated_data.get("modalidad"),
                direccion_cita=serializer.validated_data.get("direccion_cita"),
                descripcion=serializer.validated_data.get("descripcion"),
            )

            self.registrar_bitacora(
                accion=BitacoraAccion.CITA_AGENDADA_DESDE_AGENDA,
                descripcion=f"Cita #{cita.id_cita} agendada correctamente desde el módulo de agenda.",
                modulo=BitacoraModulo.AGENDA_DISPONIBILIDAD,
                entidad_id=cita.id_cita,
                resultado=BitacoraResultado.EXITO,
                metadatos={
                    "mascota_id": cita.mascota_id,
                    "servicio_id": cita.servicio_id,
                },
            )

            return Response(CitaSerializer(cita).data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.CITA_SOLICITUD_FALLIDA,
                descripcion="Falló la solicitud de cita por errores de validación.",
                modulo=BitacoraModulo.CITAS,
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": e.detail},
            )
            raise


class CitaDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_CITAS"

    def get_object(self, request, pk):
        return CitaSelector.get_cita_detail(pk, self.get_tenant_id())

    @extend_schema(
        tags=["Citas"],
        operation_id="gestion_servicios_citas_retrieve",
        responses={200: CitaSerializer, 404: OpenApiResponse(description="No encontrado.")},
    )
    def get(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            self.registrar_bitacora(
                accion=BitacoraAccion.RESERVA_CONSULTADA,
                descripcion="Falló la consulta de cita: no encontrada o sin acceso.",
                modulo=BitacoraModulo.CITAS,
                entidad_tipo="Cita",
                entidad_id=pk,
                resultado=BitacoraResultado.FALLO,
            )
            return Response(
                {"error": "Cita no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CitaSerializer(cita)

        self.registrar_bitacora(
            accion=BitacoraAccion.RESERVA_CONSULTADA,
            descripcion=f"Consulta al detalle de la reserva #{pk}.",
            modulo=BitacoraModulo.CITAS,
            entidad_tipo="Cita",
            entidad_id=getattr(cita, "id_cita", pk),
            resultado=BitacoraResultado.EXITO,
        )

        return Response(serializer.data)

    @extend_schema(
        tags=["Citas"],
        request=CitaSerializer,
        responses={200: CitaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def put(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            return Response({"error": "Cita no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CitaSerializer(cita, data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()

            self.registrar_bitacora(
                accion=BitacoraAccion.RESERVA_MODIFICADA,
                descripcion=f"Reserva #{pk} modificada manualmente.",
                modulo=BitacoraModulo.CITAS,
                entidad_id=pk,
                resultado=BitacoraResultado.EXITO,
            )
            return Response(serializer.data)
        except ValidationError as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.ACTUALIZAR,
                descripcion="Falló la actualización de cita por validación.",
                modulo=BitacoraModulo.CITAS,
                entidad_id=pk,
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": e.detail},
            )
            raise

    @extend_schema(
        tags=["Citas"],
        responses={200: OpenApiResponse(description="Estado actualizado.")},
    )
    def delete(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            return Response({"error": "Cita no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        nuevo_estado = "CANCELADA" if cita.estado != "CANCELADA" else "PENDIENTE"
        CitaService.actualizar_estado(cita, nuevo_estado)

        accion = BitacoraAccion.RESERVA_ACTIVADA if cita.estado == "PENDIENTE" else BitacoraAccion.RESERVA_CANCELADA
        self.registrar_bitacora(
            accion=accion,
            descripcion=f"La reserva #{pk} ha sido {'reactivada' if cita.estado == 'PENDIENTE' else 'cancelada'}.",
            modulo=BitacoraModulo.CITAS,
            entidad_id=pk,
            resultado=BitacoraResultado.EXITO,
            metadatos={"estado": cita.estado},
        )

        return Response(
            {
                "message": "Estado de la cita actualizado correctamente",
                "estado": cita.estado,
            },
            status=status.HTTP_200_OK,
        )


class CitaEstadoUpdateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_CITAS"

    def get_object(self, request, pk):
        return CitaSelector.get_cita_detail(pk, self.get_tenant_id())

    @extend_schema(
        tags=["Citas"],
        request=CitaEstadoUpdateSerializer,
        responses={200: CitaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def patch(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            return Response({"error": "Cita no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CitaEstadoUpdateSerializer(cita, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            
            # Reprogramación si vienen datos de tiempo
            if "fecha_programada" in serializer.validated_data or "hora_inicio" in serializer.validated_data:
                CitaService.reprogramar_cita(
                    cita, 
                    serializer.validated_data.get("fecha_programada", cita.fecha_programada),
                    serializer.validated_data.get("hora_inicio", cita.hora_inicio),
                    serializer.validated_data.get("hora_fin", cita.hora_fin)
                )
            
            # Cambio de estado si viene
            if "estado" in serializer.validated_data:
                CitaService.actualizar_estado(cita, serializer.validated_data.get("estado"))

            # Bitácora específica si es confirmación
                accion_confirmar = BitacoraAccion.CITA_CONFIRMADA_DESDE_AGENDA if serializer.validated_data.get("estado") == "CONFIRMADA" else BitacoraAccion.RESERVA_MODIFICADA
                self.registrar_bitacora(
                    accion=accion_confirmar,
                    descripcion=f"Reserva #{pk} actualizada/confirmada desde la agenda.",
                    modulo=BitacoraModulo.AGENDA_DISPONIBILIDAD,
                    entidad_id=pk,
                    resultado=BitacoraResultado.EXITO,
                )
            return Response(CitaSerializer(cita).data)
        except ValidationError as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.RESERVA_MODIFICACION_FALLIDA,
                descripcion="Falló la actualización de reserva.",
                modulo=BitacoraModulo.CITAS,
                entidad_id=pk,
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": e.detail},
            )
            raise
