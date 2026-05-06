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
from ..selectors.servicios_selector import CategoriaSelector
from ..serializers.categoriaservicio_serializer import CategoriaServicioSerializer





class CategoriaServicioListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_CATEGORIAS"

    @extend_schema(
        tags=["Servicios"],
        operation_id="gestion_servicios_categorias_list",
        responses={200: CategoriaServicioSerializer},
    )
    def get(self, request):
        categorias = CategoriaSelector.get_categorias_by_tenant(self.get_tenant_id())
        serializer = CategoriaServicioSerializer(categorias, many=True)

        self.registrar_bitacora(
            accion=BitacoraAccion.CATEGORIA_SERVICIO_CONSULTADA,
            descripcion="Listado de categorías de servicio consultado.",
            modulo=BitacoraModulo.CATALOGOS,
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": categorias.count()},
        )

        return Response(serializer.data)

    @extend_schema(
        tags=["Servicios"],
        request=CategoriaServicioSerializer,
        responses={201: CategoriaServicioSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def post(self, request):
        serializer = CategoriaServicioSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            categoria = serializer.save(veterinaria_id=self.get_tenant_id())

            self.registrar_bitacora(
                accion=BitacoraAccion.CATEGORIA_SERVICIO_CREADA,
                descripcion=f"Categoría de servicio '{categoria.nombre}' creada.",
                modulo=BitacoraModulo.CATALOGOS,
                entidad_id=categoria.id_categoria,
                resultado=BitacoraResultado.EXITO,
                metadatos={"nombre": categoria.nombre},
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.SERVICIO_CREADO,
                descripcion="Falló la creación de categoría de servicio.",
                modulo=BitacoraModulo.CATALOGOS,
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": e.detail},
            )
            raise


class CategoriaServicioDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_CATEGORIAS"

    def get_object(self, request, pk):
        from ..models import CategoriaServicio
        try:
            return CategoriaServicio.objects.get(pk=pk, veterinaria_id=self.get_tenant_id())
        except CategoriaServicio.DoesNotExist:
            return None

    @extend_schema(
        tags=["Servicios"],
        operation_id="gestion_servicios_categorias_retrieve",
        responses={200: CategoriaServicioSerializer, 404: OpenApiResponse(description="No encontrado.")},
    )
    def get(self, request, pk):
        categoria = self.get_object(request, pk)
        if not categoria:
            return Response({"error": "Categoría no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CategoriaServicioSerializer(categoria)
        self.registrar_bitacora(
            accion="CATEGORIA_SERVICIO_CONSULTADA",
            descripcion="Detalle de categoría de servicio consultado.",
            modulo=BitacoraModulo.CATALOGOS,
            entidad_id=pk,
            resultado=BitacoraResultado.EXITO,
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["Servicios"],
        request=CategoriaServicioSerializer,
        responses={200: CategoriaServicioSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def put(self, request, pk):
        categoria = self.get_object(request, pk)
        if not categoria:
            return Response({"error": "Categoría no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CategoriaServicioSerializer(categoria, data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()

            self.registrar_bitacora(
                accion=BitacoraAccion.CATEGORIA_SERVICIO_EDITADA,
                descripcion=f"Categoría de servicio '{categoria.nombre}' actualizada.",
                modulo=BitacoraModulo.CATALOGOS,
                entidad_id=pk,
                resultado=BitacoraResultado.EXITO,
            )
            return Response(serializer.data)
        except ValidationError as e:
            self.registrar_bitacora(
                accion=BitacoraAccion.SERVICIO_EDITADO,
                descripcion="Falló la actualización de categoría de servicio por validación.",
                modulo=BitacoraModulo.CATALOGOS,
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
        categoria = self.get_object(request, pk)
        if not categoria:
            return Response({"error": "Categoría no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        categoria.estado = not categoria.estado
        categoria.save()

        accion = "CATEGORIA_SERVICIO_ACTIVADA" if categoria.estado else "CATEGORIA_SERVICIO_DESACTIVADA"
        self.registrar_bitacora(
            accion=accion,
            descripcion=f"Estado de la categoría '{categoria.nombre}' actualizado.",
            modulo=BitacoraModulo.CATALOGOS,
            entidad_id=pk,
            resultado=BitacoraResultado.EXITO,
            metadatos={"estado": categoria.estado},
        )

        return Response({
            "message": "Estado de la categoría actualizado correctamente",
            "estado": categoria.estado
        }, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(operation_id="gestion_servicios_categorias_retrieve_legacy"),
    put=extend_schema(operation_id="gestion_servicios_categorias_update_legacy"),
    delete=extend_schema(operation_id="gestion_servicios_categorias_delete_legacy"),
)
class CategoriaServicioDetailLegacyView(CategoriaServicioDetailView):
    pass
