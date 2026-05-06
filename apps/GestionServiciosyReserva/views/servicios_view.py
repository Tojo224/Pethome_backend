from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)
from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.selectors.perfil_selector import SuscripcionSelector
from ..selectors.servicios_selector import ServicioSelector
from ..serializers.servicios_serializer import ServicioSerializer





class ServicioListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_SERVICIOS"

    @extend_schema(
        tags=["Servicios"],
        operation_id="gestion_servicios_list",
        responses={200: ServicioSerializer},
    )
    def get(self, request):
        vet_id = self.get_tenant_id()
        user = request.user
        
        # --- REGLA SaaS: Validación de App Móvil por Plan ---
        plataforma = request.query_params.get("plataforma")
        if plataforma == "movil" or (hasattr(user, "role") and user.role.nombre == "CLIENT"):
            suscripcion = SuscripcionSelector.get_suscripcion_activa(vet_id)
            if suscripcion and not suscripcion.plan.permite_app_movil:
                return Response(
                    {"detail": "Su plan actual no permite el acceso al catálogo desde la aplicación móvil."},
                    status=status.HTTP_403_FORBIDDEN
                )

        solo_activos = (hasattr(user, "role") and user.role.nombre == "CLIENT")
        servicios = ServicioSelector.get_servicios_by_tenant(vet_id, solo_activos=solo_activos)
            
        serializer = ServicioSerializer(servicios, many=True)

        self.registrar_bitacora(
            accion=BitacoraAccion.SERVICIO_CONSULTADO,
            descripcion="Listado de servicios consultado.",
            metadatos={"total": servicios.count()},
        )

        return Response(serializer.data)

    @extend_schema(
        tags=["Servicios"],
        request=ServicioSerializer,
        responses={201: ServicioSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def post(self, request):
        serializer = ServicioSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            servicio = serializer.save(veterinaria_id=self.get_tenant_id())

            self.registrar_bitacora(
                accion=BitacoraAccion.SERVICIO_CREADO,
                descripcion=f"Servicio '{servicio.nombre}' creado.",
                modulo=BitacoraModulo.SERVICIOS,
                entidad_id=servicio.id_servicio,
                resultado=BitacoraResultado.EXITO,
                metadatos={"nombre": servicio.nombre},
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.CREAR,
                descripcion="Falló la creación de servicio.",
                modulo=BitacoraModulo.SERVICIOS,
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": e.detail},
            )
            raise


class ServicioDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_SERVICIOS"

    def get_object(self, request, pk):
        return ServicioSelector.get_servicio_detail(pk, self.get_tenant_id())

    @extend_schema(
        tags=["Servicios"],
        operation_id="gestion_servicios_retrieve",
        responses={200: ServicioSerializer, 404: OpenApiResponse(description="No encontrado.")},
    )
    def get(self, request, pk):
        servicio = self.get_object(request, pk)
        if not servicio:
            return Response({"error": "Servicio no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ServicioSerializer(servicio)
        self.registrar_bitacora(
            accion=BitacoraAccion.SERVICIO_CONSULTADO,
            descripcion="Detalle de servicio consultado.",
            modulo=BitacoraModulo.SERVICIOS,
            entidad_id=pk,
            resultado=BitacoraResultado.EXITO,
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["Servicios"],
        request=ServicioSerializer,
        responses={200: ServicioSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def put(self, request, pk):
        servicio = self.get_object(request, pk)
        if not servicio:
            return Response({"error": "Servicio no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ServicioSerializer(servicio, data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()

            self.registrar_bitacora(
                accion=BitacoraAccion.SERVICIO_EDITADO,
                descripcion=f"Servicio '{servicio.nombre}' actualizado.",
                modulo=BitacoraModulo.SERVICIOS,
                entidad_id=pk,
                resultado=BitacoraResultado.EXITO,
            )
            return Response(serializer.data)
        except ValidationError as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.ACTUALIZAR,
                descripcion="Falló la actualización de servicio por validación.",
                modulo=BitacoraModulo.SERVICIOS,
                entidad_id=pk,
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": e.detail},
            )
            raise

    @extend_schema(
        tags=["Servicios"],
        responses={200: OpenApiResponse(description="Estado actualizado.")},
    )
    def delete(self, request, pk):
        servicio = self.get_object(request, pk)
        if not servicio:
            return Response({"error": "Servicio no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        servicio.estado = not servicio.estado
        servicio.save()

        accion_bit = BitacoraAccion.SERVICIO_ACTIVADO if servicio.estado else BitacoraAccion.SERVICIO_DESACTIVADO
        self.registrar_bitacora(
            accion=accion_bit,
            descripcion=f"Estado del servicio '{servicio.nombre}' actualizado.",
            modulo=BitacoraModulo.SERVICIOS,
            entidad_id=pk,
            resultado=BitacoraResultado.EXITO,
            metadatos={"estado": servicio.estado},
        )

        return Response({
            "message": "Estado actualizado correctamente",
            "estado": servicio.estado
        }, status=status.HTTP_200_OK)
