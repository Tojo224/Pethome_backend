from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraModulo,
    BitacoraResultado,
    BitacoraAccion,
)
from apps.GestionClientesyMascotas.selectors.mascota_selector import MascotaSelector

from ..selectors.clinica_selector import HistorialClinicoSelector
from ..serializers.historial_clinico_serializer import HistorialClinicoSerializer
from ..models.historial_clinico import HistorialClinico


class HistorialClinicoListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_HISTORIALES"

    @extend_schema(
        tags=["Clinica"],
        responses={200: HistorialClinicoSerializer(many=True)},
        description="Lista todos los historiales clínicos de la veterinaria actual.",
    )
    def get(self, request):
        vet_id = self.get_tenant_id()
        historiales = HistorialClinicoSelector.get_historiales_by_tenant(
            vet_id,
            user=request.user,
        )
        serializer = HistorialClinicoSerializer(historiales, many=True)

        self.registrar_bitacora(
            accion=BitacoraAccion.HISTORIAL_CLINICO_CONSULTADO,
            descripcion="Listado de historiales clínicos consultado.",
            modulo=BitacoraModulo.CLINICA,
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": historiales.count()},
        )

        return Response(serializer.data)

    @extend_schema(
        tags=["Clinica"],
        request=HistorialClinicoSerializer,
        responses={
            201: HistorialClinicoSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
        },
        description="Crea un historial clínico para una mascota del tenant actual.",
    )
    def post(self, request):
        vet_id = self.get_tenant_id()
        serializer = HistorialClinicoSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        mascota = serializer.validated_data.get("mascota")

        mascota_autorizada = MascotaSelector.get_mascota_detail(
            mascota.pk,
            vet_id,
            user=request.user,
        )

        if not mascota_autorizada:
            self.registrar_bitacora(
                accion=BitacoraAccion.ACCESO_DENEGADO,
                descripcion=f"Intento de crear historial para mascota ID {mascota.pk} fuera del tenant.",
                modulo=BitacoraModulo.CLINICA,
                resultado=BitacoraResultado.FALLO,
            )
            return Response(
                {"error": "Mascota no encontrada en su veterinaria."},
                status=status.HTTP_404_NOT_FOUND,
            )

        historial = serializer.save()

        self.registrar_bitacora(
            accion=BitacoraAccion.HISTORIAL_CLINICO_CREADO,
            descripcion=f"Historial clínico creado para la mascota '{mascota_autorizada.nombre}'.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=historial.pk,
            resultado=BitacoraResultado.EXITO,
        )

        return Response(
            HistorialClinicoSerializer(historial).data,
            status=status.HTTP_201_CREATED,
        )


class HistorialClinicoDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_HISTORIALES"

    def get_historial_validado(self, request, id_historial_clinico):
        vet_id = self.get_tenant_id()

        try:
            historial = HistorialClinico.objects.select_related("mascota").get(
                id_historial_clinico=id_historial_clinico
            )
        except HistorialClinico.DoesNotExist:
            return None, Response(
                {"error": "Historial clínico no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        mascota_autorizada = MascotaSelector.get_mascota_detail(
            historial.mascota.pk,
            vet_id,
            user=request.user,
        )

        if not mascota_autorizada:
            self.registrar_bitacora(
                accion=BitacoraAccion.ACCESO_DENEGADO,
                descripcion=f"Intento de acceso a historial clínico ID {id_historial_clinico} fuera del tenant.",
                modulo=BitacoraModulo.CLINICA,
                resultado=BitacoraResultado.FALLO,
            )

            return None, Response(
                {"error": "Historial clínico no encontrado en su veterinaria."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return historial, None

    @extend_schema(
        tags=["Clinica"],
        responses={
            200: HistorialClinicoSerializer,
            404: OpenApiResponse(description="No encontrado."),
        },
        description="Obtiene un historial clínico específico validando el tenant.",
    )
    def get(self, request, id_historial_clinico):
        historial, error_response = self.get_historial_validado(
            request,
            id_historial_clinico,
        )

        if error_response:
            return error_response

        serializer = HistorialClinicoSerializer(historial)

        self.registrar_bitacora(
            accion=BitacoraAccion.HISTORIAL_CLINICO_CONSULTADO,
            descripcion=f"Historial clínico ID {id_historial_clinico} consultado.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=historial.pk,
            resultado=BitacoraResultado.EXITO,
        )

        return Response(serializer.data)

    @extend_schema(
        tags=["Clinica"],
        request=HistorialClinicoSerializer,
        responses={
            200: HistorialClinicoSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            404: OpenApiResponse(description="No encontrado."),
        },
        description="Actualiza parcialmente un historial clínico validando el tenant.",
    )
    def patch(self, request, id_historial_clinico):
        historial, error_response = self.get_historial_validado(
            request,
            id_historial_clinico,
        )

        if error_response:
            return error_response

        serializer = HistorialClinicoSerializer(
            historial,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        historial_actualizado = serializer.save()

        accion_actualizar = getattr(
            BitacoraAccion,
            "HISTORIAL_CLINICO_ACTUALIZADO",
            BitacoraAccion.HISTORIAL_CLINICO_CONSULTADO,
        )

        self.registrar_bitacora(
            accion=accion_actualizar,
            descripcion=f"Historial clínico ID {id_historial_clinico} actualizado.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=historial_actualizado.pk,
            resultado=BitacoraResultado.EXITO,
        )

        return Response(HistorialClinicoSerializer(historial_actualizado).data)

    @extend_schema(
        tags=["Clinica"],
        request=HistorialClinicoSerializer,
        responses={
            200: HistorialClinicoSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            404: OpenApiResponse(description="No encontrado."),
        },
        description="Actualiza completamente un historial clínico validando el tenant.",
    )
    def put(self, request, id_historial_clinico):
        historial, error_response = self.get_historial_validado(
            request,
            id_historial_clinico,
        )

        if error_response:
            return error_response

        serializer = HistorialClinicoSerializer(
            historial,
            data=request.data,
            partial=False,
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        historial_actualizado = serializer.save()

        accion_actualizar = getattr(
            BitacoraAccion,
            "HISTORIAL_CLINICO_ACTUALIZADO",
            BitacoraAccion.HISTORIAL_CLINICO_CONSULTADO,
        )

        self.registrar_bitacora(
            accion=accion_actualizar,
            descripcion=f"Historial clínico ID {id_historial_clinico} actualizado completamente.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=historial_actualizado.pk,
            resultado=BitacoraResultado.EXITO,
        )

        return Response(HistorialClinicoSerializer(historial_actualizado).data)


class HistorialClinicoPorMascotaView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_HISTORIALES"

    @extend_schema(
        tags=["Clinica"],
        responses={
            200: HistorialClinicoSerializer,
            404: OpenApiResponse(description="No encontrado."),
        },
        description="Obtiene o crea el historial clínico de una mascota específica, validando el tenant.",
    )
    def get(self, request, id_mascota):
        vet_id = self.get_tenant_id()

        mascota = MascotaSelector.get_mascota_detail(
            id_mascota,
            vet_id,
            user=request.user,
        )

        if not mascota:
            self.registrar_bitacora(
                accion=BitacoraAccion.ACCESO_DENEGADO,
                descripcion=f"Intento de acceso a mascota ID {id_mascota} de otro tenant o propietario.",
                modulo=BitacoraModulo.CLINICA,
                resultado=BitacoraResultado.FALLO,
            )
            return Response(
                {"error": "Mascota no encontrada en su veterinaria."},
                status=status.HTTP_404_NOT_FOUND,
            )

        historial, creado = HistorialClinico.objects.get_or_create(
            mascota=mascota,
            defaults={"estado": True},
        )

        if creado:
            self.registrar_bitacora(
                accion=BitacoraAccion.HISTORIAL_CLINICO_CREADO,
                descripcion=f"Historial clínico creado para la mascota '{mascota.nombre}'.",
                modulo=BitacoraModulo.CLINICA,
                entidad_id=historial.pk,
                resultado=BitacoraResultado.EXITO,
            )

        serializer = HistorialClinicoSerializer(historial)

        self.registrar_bitacora(
            accion=BitacoraAccion.HISTORIAL_CLINICO_CONSULTADO,
            descripcion=f"Historial clínico de '{mascota.nombre}' consultado.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=historial.pk,
            resultado=BitacoraResultado.EXITO,
        )

        return Response(serializer.data)