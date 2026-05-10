from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraModulo, BitacoraResultado, BitacoraAccion
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
        description="Lista todos los historiales clínicos de la veterinaria actual."
    )
    def get(self, request):
        vet_id = self.get_tenant_id()
        historiales = HistorialClinicoSelector.get_historiales_by_tenant(vet_id, user=request.user)
        serializer = HistorialClinicoSerializer(historiales, many=True)
        
        self.registrar_bitacora(
            accion=BitacoraAccion.HISTORIAL_CLINICO_CONSULTADO,
            descripcion="Listado de historiales clínicos consultado.",
            modulo=BitacoraModulo.CLINICA,
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": historiales.count()}
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["Clinica"],
        request=HistorialClinicoSerializer,
        responses={201: HistorialClinicoSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
        description="Crea un historial clínico para una mascota del tenant actual."
    )
    def post(self, request):
        vet_id = self.get_tenant_id()
        serializer = HistorialClinicoSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        mascota = serializer.validated_data.get("mascota")
        mascota_autorizada = MascotaSelector.get_mascota_detail(mascota.pk, vet_id, user=request.user)
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

        return Response(HistorialClinicoSerializer(historial).data, status=status.HTTP_201_CREATED)

class HistorialClinicoPorMascotaView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_HISTORIALES"

    @extend_schema(
        tags=["Clinica"], 
        responses={200: HistorialClinicoSerializer, 404: OpenApiResponse(description="No encontrado.")},
        description="Obtiene o crea el historial clínico de una mascota específica, validando el tenant."
    )
    def get(self, request, id_mascota):
        vet_id = self.get_tenant_id()
        
        # Validar que la mascota pertenece al tenant y al cliente (si aplica)
        mascota = MascotaSelector.get_mascota_detail(id_mascota, vet_id, user=request.user)
        if not mascota:
            self.registrar_bitacora(
                accion=BitacoraAccion.ACCESO_DENEGADO,
                descripcion=f"Intento de acceso a mascota ID {id_mascota} de otro tenant o propietario.",
                modulo=BitacoraModulo.CLINICA,
                resultado=BitacoraResultado.FALLO
            )
            return Response({"error": "Mascota no encontrada en su veterinaria."}, status=status.HTTP_404_NOT_FOUND)

        # Buscar o crear historial (Regla SaaS: una mascota = un historial)
        historial, creado = HistorialClinico.objects.get_or_create(
            mascota=mascota,
            defaults={"estado": True}
        )
        
        if creado:
            self.registrar_bitacora(
                accion=BitacoraAccion.HISTORIAL_CLINICO_CREADO,
                descripcion=f"Historial clínico creado para la mascota '{mascota.nombre}'.",
                modulo=BitacoraModulo.CLINICA,
                entidad_id=historial.pk,
                resultado=BitacoraResultado.EXITO
            )

        serializer = HistorialClinicoSerializer(historial)
        
        self.registrar_bitacora(
            accion=BitacoraAccion.HISTORIAL_CLINICO_CONSULTADO,
            descripcion=f"Historial clínico de '{mascota.nombre}' consultado.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=historial.pk,
            resultado=BitacoraResultado.EXITO
        )
        return Response(serializer.data)
