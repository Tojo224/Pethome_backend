from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view

from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)
from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from ..selectors.servicios_selector import PrecioServicioSelector
from ..serializers.precioservicio_serializer import PrecioServicioSerializer





class PrecioServicioListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_PRECIOS"

    @extend_schema(
        tags=["Servicios"],
        operation_id="gestion_servicios_precios_list",
        responses={200: PrecioServicioSerializer},
    )
    def get(self, request):
        precios = PrecioServicioSelector.get_precios_by_tenant(self.get_tenant_id())
        serializer = PrecioServicioSerializer(precios, many=True)

        self.registrar_bitacora(
            accion=BitacoraAccion.PRECIO_SERVICIO_CONSULTADO,
            descripcion="Listado de precios de servicio consultado.",
            modulo=BitacoraModulo.PRECIOS,
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": precios.count()},
        )

        return Response(serializer.data)

    @extend_schema(
        tags=["Servicios"],
        request=PrecioServicioSerializer,
        responses={201: PrecioServicioSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def post(self, request):
        serializer = PrecioServicioSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            precio = serializer.save(veterinaria_id=self.get_tenant_id())

            self.registrar_bitacora(
                accion=BitacoraAccion.PRECIO_SERVICIO_CREADO,
                descripcion=f"Precio para el servicio ID {precio.servicio_id} creado.",
                modulo=BitacoraModulo.PRECIOS,
                entidad_id=precio.id_precio,
                resultado=BitacoraResultado.EXITO,
                metadatos={"servicio_id": precio.servicio_id},
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.CREAR,
                descripcion="Falló la creación de precio de servicio.",
                modulo=BitacoraModulo.PRECIOS,
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": e.detail},
            )
            raise


class PrecioServicioDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_PRECIOS"

    def get_object(self, request, pk):
        from ..models import PrecioServicio
        try:
            return PrecioServicio.objects.get(pk=pk, veterinaria_id=self.get_tenant_id())
        except PrecioServicio.DoesNotExist:
            return None

    @extend_schema(
        tags=["Servicios"],
        operation_id="gestion_servicios_precios_retrieve",
        responses={200: PrecioServicioSerializer, 404: OpenApiResponse(description="No encontrado.")},
    )
    def get(self, request, pk):
        precio = self.get_object(request, pk)
        if not precio:
            return Response({"error": "Precio no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        serializer = PrecioServicioSerializer(precio)
        self.registrar_bitacora(
            accion="PRECIO_SERVICIO_CONSULTADO",
            descripcion="Detalle de precio de servicio consultado.",
            modulo=BitacoraModulo.PRECIOS,
            entidad_id=pk,
            resultado=BitacoraResultado.EXITO,
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["Servicios"],
        request=PrecioServicioSerializer,
        responses={200: PrecioServicioSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def put(self, request, pk):
        precio = self.get_object(request, pk)
        if not precio:
            return Response({"error": "Precio no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        serializer = PrecioServicioSerializer(precio, data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()

            self.registrar_bitacora(
                accion=BitacoraAccion.PRECIO_SERVICIO_EDITADO,
                descripcion=f"Precio ID {pk} actualizado.",
                modulo=BitacoraModulo.PRECIOS,
                entidad_id=pk,
                resultado=BitacoraResultado.EXITO,
            )
            return Response(serializer.data)
        except ValidationError as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.ACTUALIZAR,
                descripcion="Falló la actualización de precio por validación.",
                modulo=BitacoraModulo.PRECIOS,
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
        precio = self.get_object(request, pk)
        if not precio:
            return Response({"error": "Precio no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        precio.estado = not precio.estado
        precio.save()

        accion = "PRECIO_SERVICIO_ACTIVADO" if precio.estado else "PRECIO_SERVICIO_DESACTIVADO"
        self.registrar_bitacora(
            accion=accion,
            descripcion=f"Estado del precio ID {pk} actualizado.",
            modulo=BitacoraModulo.PRECIOS,
            entidad_id=pk,
            resultado=BitacoraResultado.EXITO,
            metadatos={"estado": precio.estado},
        )

        return Response({
            "message": "Estado del precio actualizado correctamente",
            "estado": precio.estado
        }, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(operation_id="gestion_servicios_precios_retrieve_legacy"),
    put=extend_schema(operation_id="gestion_servicios_precios_update_legacy"),
    delete=extend_schema(operation_id="gestion_servicios_precios_delete_legacy"),
)
class PrecioServicioDetailLegacyView(PrecioServicioDetailView):
    pass
