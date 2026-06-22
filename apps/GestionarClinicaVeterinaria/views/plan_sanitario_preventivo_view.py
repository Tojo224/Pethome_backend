from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)
from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.models.user import User
from apps.GestionClientesyMascotas.selectors.mascota_selector import MascotaSelector

from ..selectors.clinica_selector import PlanSanitarioPreventivoSelector
from ..serializers.plan_sanitario_preventivo_serializer import (
    PlanSanitarioPreventivoSerializer,
)


def _get_role_name(user):
    return (getattr(getattr(user, "role", None), "nombre", "") or "").upper()


def _is_staff_clinico(user):
    return _get_role_name(user) in {RoleEnum.ADMIN.value, RoleEnum.VETERINARIAN.value}


class PlanSanitarioClienteFilterSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id_usuario", "nombre"]

    def get_nombre(self, obj):
        perfil = getattr(obj, "perfil", None)
        if perfil and getattr(perfil, "nombre", None):
            return perfil.nombre
        return getattr(obj, "correo", f"Usuario {obj.id_usuario}")


class PlanSanitarioClientesFilterView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_PLAN_SANITARIO"

    @extend_schema(
        tags=["Clinica"],
        responses={200: PlanSanitarioClienteFilterSerializer(many=True)},
        description="Lista clientes disponibles para filtros del plan sanitario preventivo.",
    )
    def get(self, request):
        if not _is_staff_clinico(request.user):
            return Response(
                {"detail": "No tienes permisos para consultar la lista de clientes del plan sanitario."},
                status=status.HTTP_403_FORBIDDEN,
            )

        clientes = User.objects.filter(
            role__nombre=RoleEnum.CLIENT.value,
            is_active=True,
            veterinaria_id=self.get_tenant_id(),
        ).select_related("perfil").order_by("id_usuario")

        self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_CONSULTADO,
            descripcion="Listado de clientes para filtros del plan sanitario consultado.",
            modulo=BitacoraModulo.CLINICA,
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": clientes.count()},
        )

        return Response(PlanSanitarioClienteFilterSerializer(clientes, many=True).data)


class PlanSanitarioPorMascotaView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_PLAN_SANITARIO"

    def _get_mascota_autorizada(self, request, id_mascota):
        vet_id = self.get_tenant_id()
        mascota = MascotaSelector.get_mascota_detail(
            id_mascota,
            vet_id,
            user=request.user,
        )
        if not mascota:
            self.registrar_bitacora(
                accion=BitacoraAccion.ACCESO_DENEGADO,
                descripcion=f"Intento de acceso a plan sanitario de mascota ID {id_mascota} fuera del tenant.",
                modulo=BitacoraModulo.CLINICA,
                resultado=BitacoraResultado.FALLO,
            )
        return mascota

    @extend_schema(
        tags=["Clinica"],
        responses={200: PlanSanitarioPreventivoSerializer(many=True)},
        description="Lista los elementos del plan sanitario preventivo de una mascota.",
    )
    def get(self, request, id_mascota):
        mascota = self._get_mascota_autorizada(request, id_mascota)
        if not mascota:
            return Response(
                {"error": "Mascota no encontrada en su veterinaria."},
                status=status.HTTP_404_NOT_FOUND,
            )

        planes = PlanSanitarioPreventivoSelector.get_planes_by_mascota(
            mascota.id_mascota,
            self.get_tenant_id(),
        )

        self.registrar_bitacora(
            accion=BitacoraAccion.HISTORIAL_CLINICO_CONSULTADO,
            descripcion=f"Plan sanitario de la mascota '{mascota.nombre}' consultado.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=mascota.id_mascota,
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": planes.count()},
        )

        return Response(PlanSanitarioPreventivoSerializer(planes, many=True).data)

    @extend_schema(
        tags=["Clinica"],
        request=PlanSanitarioPreventivoSerializer,
        responses={
            201: PlanSanitarioPreventivoSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            403: OpenApiResponse(description="Sin permisos para crear."),
        },
        description="Crea un elemento del plan sanitario preventivo para una mascota.",
    )
    def post(self, request, id_mascota):
        if not _is_staff_clinico(request.user):
            return Response(
                {"error": "No tiene permisos para crear elementos del plan sanitario."},
                status=status.HTTP_403_FORBIDDEN,
            )

        mascota = self._get_mascota_autorizada(request, id_mascota)
        if not mascota:
            return Response(
                {"error": "Mascota no encontrada en su veterinaria."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PlanSanitarioPreventivoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        plan = serializer.save(
            mascota=mascota,
            veterinaria_id=self.get_tenant_id(),
            usuario_registro=request.user,
        )

        self.registrar_bitacora(
            accion=BitacoraAccion.CREAR,
            descripcion=f"Plan sanitario creado para la mascota '{mascota.nombre}'.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=plan.id_plan_sanitario,
            resultado=BitacoraResultado.EXITO,
        )

        return Response(
            PlanSanitarioPreventivoSerializer(plan).data,
            status=status.HTTP_201_CREATED,
        )


class PlanSanitarioDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_PLAN_SANITARIO"

    def _get_plan_autorizado(self, request, id_plan):
        plan = PlanSanitarioPreventivoSelector.get_plan_detail(
            id_plan,
            self.get_tenant_id(),
        )
        if not plan:
            return None

        mascota = MascotaSelector.get_mascota_detail(
            plan.mascota_id,
            self.get_tenant_id(),
            user=request.user,
        )
        if not mascota:
            self.registrar_bitacora(
                accion=BitacoraAccion.ACCESO_DENEGADO,
                descripcion=f"Intento de acceso a plan sanitario ID {id_plan} fuera del tenant.",
                modulo=BitacoraModulo.CLINICA,
                resultado=BitacoraResultado.FALLO,
            )
            return None
        return plan

    @extend_schema(
        tags=["Clinica"],
        responses={
            200: PlanSanitarioPreventivoSerializer,
            404: OpenApiResponse(description="No encontrado."),
        },
        description="Obtiene el detalle de un elemento del plan sanitario preventivo.",
    )
    def get(self, request, id_plan):
        plan = self._get_plan_autorizado(request, id_plan)
        if not plan:
            return Response(
                {"error": "Plan sanitario no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.registrar_bitacora(
            accion=BitacoraAccion.VISUALIZAR,
            descripcion=f"Plan sanitario ID {id_plan} consultado.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=plan.id_plan_sanitario,
            resultado=BitacoraResultado.EXITO,
        )
        return Response(PlanSanitarioPreventivoSerializer(plan).data)

    @extend_schema(
        tags=["Clinica"],
        request=PlanSanitarioPreventivoSerializer,
        responses={
            200: PlanSanitarioPreventivoSerializer,
            400: OpenApiResponse(description="Datos inválidos."),
            403: OpenApiResponse(description="Sin permisos para editar."),
            404: OpenApiResponse(description="No encontrado."),
        },
        description="Actualiza parcialmente un elemento del plan sanitario preventivo.",
    )
    def patch(self, request, id_plan):
        if not _is_staff_clinico(request.user):
            return Response(
                {"error": "No tiene permisos para editar elementos del plan sanitario."},
                status=status.HTTP_403_FORBIDDEN,
            )

        plan = self._get_plan_autorizado(request, id_plan)
        if not plan:
            return Response(
                {"error": "Plan sanitario no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PlanSanitarioPreventivoSerializer(
            plan,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        plan_actualizado = serializer.save()

        self.registrar_bitacora(
            accion=BitacoraAccion.ACTUALIZAR,
            descripcion=f"Plan sanitario ID {id_plan} actualizado.",
            modulo=BitacoraModulo.CLINICA,
            entidad_id=plan_actualizado.id_plan_sanitario,
            resultado=BitacoraResultado.EXITO,
        )

        return Response(PlanSanitarioPreventivoSerializer(plan_actualizado).data)
