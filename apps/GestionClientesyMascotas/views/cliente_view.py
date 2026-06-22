from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema

from apps.AutenticacionySeguridad.models import Perfil, Rol
from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)
from rest_framework.permissions import IsAuthenticated

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.serializers.perfil_serializer import (
    PerfilSerializer,
    PerfilCreateSerializer,
    PerfilUpdateSerializer,
)
from apps.AutenticacionySeguridad.services.perfil_service import deactivate_user_profile
from apps.AutenticacionySeguridad.selectors.perfil_selector import PerfilSelector
from apps.AutenticacionySeguridad.utils.audit_utils import (
    obtener_snapshot_perfil,
    construir_metadatos_actualizacion_perfil,
)





class ClientePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ClienteListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CLIENTES"

    def _is_client_role(self, request):
        return (
            getattr(getattr(request.user, "role", None), "nombre", "") or ""
        ).upper() == Rol.RolName.CLIENT

    def get_queryset(self):
        return PerfilSelector.filter_perfiles(
            veterinaria_id=self.get_tenant_id(),
            rol=Rol.RolName.CLIENT
        )

    @extend_schema(
        tags=["Clientes"],
        operation_id="gestion_clientes_list",
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, required=False),
            OpenApiParameter("estado", OpenApiTypes.STR, required=False, description="true/false"),
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False),
        ],
        responses={200: PerfilSerializer},
    )
    def get(self, request):
        if self._is_client_role(request):
            return Response(
                {"detail": "No tienes permisos para consultar la lista general de clientes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = PerfilSelector.filter_perfiles(
            veterinaria_id=self.get_tenant_id(),
            rol=Rol.RolName.CLIENT,
            search=request.query_params.get("search"),
            estado=request.query_params.get("estado")
        )

        paginator = ClientePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PerfilSerializer(page, many=True)

        self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_CONSULTADO,
            descripcion="Listado de clientes consultado.",
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="Cliente",
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "total": queryset.count(),
                "search": request.query_params.get("search", "").strip(),
                "estado": request.query_params.get("estado"),
            },
        )

        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["Clientes"],
        request=PerfilCreateSerializer,
        responses={201: PerfilSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def post(self, request):
        if self._is_client_role(request):
            return Response(
                {"detail": "No tienes permisos para crear clientes desde este endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy()

        try:
            rol_cliente = Rol.objects.get(nombre=Rol.RolName.CLIENT)
            data["id_rol"] = rol_cliente.pk
        except Rol.DoesNotExist:
            self.registrar_bitacora(
                accion=BitacoraAccion.CLIENTE_CREADO,
                descripcion="Falló la creación de cliente: rol CLIENT no configurado.",
                modulo=BitacoraModulo.CLIENTES,
                entidad_tipo="Cliente",
                resultado=BitacoraResultado.FALLO,
            )
            return Response(
                {"detail": "El rol de cliente no está configurado en el sistema."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = PerfilCreateSerializer(data=data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            self.registrar_bitacora(
                accion=BitacoraAccion.CLIENTE_CREADO,
                descripcion="Falló la creación de cliente por errores de validación.",
                modulo=BitacoraModulo.CLIENTES,
                entidad_tipo="Cliente",
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": serializer.errors},
            )
            raise

        perfil = serializer.save()

        self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_CREADO,
            descripcion="Cliente creado desde gestión de clientes.",
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="Cliente",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={"correo": getattr(perfil.usuario, "correo", "")},
        )

        return Response(PerfilSerializer(perfil).data, status=status.HTTP_201_CREATED)


class ClienteDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CLIENTES"

    def _is_client_role(self, request):
        return (
            getattr(getattr(request.user, "role", None), "nombre", "") or ""
        ).upper() == Rol.RolName.CLIENT

    def get_queryset(self):
        return PerfilSelector.filter_perfiles(
            veterinaria_id=self.get_tenant_id(),
            rol=Rol.RolName.CLIENT
        )

    def get_object(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    @extend_schema(
        tags=["Clientes"],
        operation_id="gestion_clientes_retrieve",
        responses={200: PerfilSerializer, 404: OpenApiResponse(description="No encontrado.")},
    )
    def get(self, request, pk):
        if self._is_client_role(request):
            return Response(
                {"detail": "No tienes permisos para consultar clientes desde este endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        perfil = self.get_object(pk)
        serializer = PerfilSerializer(perfil)

        self.registrar_bitacora(
            accion="CLIENTE_CONSULTADO",
            descripcion="Detalle de cliente consultado.",
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="Cliente",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={"correo_objetivo": getattr(perfil.usuario, "correo", "")},
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Clientes"],
        request=PerfilUpdateSerializer,
        responses={200: PerfilSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def put(self, request, pk):
        if self._is_client_role(request):
            return Response(
                {"detail": "No tienes permisos para editar clientes desde este endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        perfil = self.get_object(pk)
        serializer = PerfilUpdateSerializer(perfil, data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            self.registrar_bitacora(
                accion=BitacoraAccion.CLIENTE_EDITADO,
                descripcion="Falló la actualización completa de cliente.",
                modulo=BitacoraModulo.CLIENTES,
                entidad_tipo="Cliente",
                entidad_id=getattr(perfil.usuario, "id_usuario", ""),
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": serializer.errors},
            )
            raise

        snapshot_antes = obtener_snapshot_perfil(perfil)
        perfil = serializer.save()
        perfil = Perfil.objects.select_related("usuario", "usuario__role").get(pk=perfil.pk)
        snapshot_despues = obtener_snapshot_perfil(perfil)
        metadatos_cambios = construir_metadatos_actualizacion_perfil(
            snapshot_antes,
            snapshot_despues,
            serializer.validated_data,
        )

        self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_EDITADO,
            descripcion="Cliente actualizado.",
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="Cliente",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos=metadatos_cambios,
        )

        return Response(PerfilSerializer(perfil).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Clientes"],
        request=PerfilUpdateSerializer,
        responses={200: PerfilSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def patch(self, request, pk):
        if self._is_client_role(request):
            return Response(
                {"detail": "No tienes permisos para editar clientes desde este endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        perfil = self.get_object(pk)
        serializer = PerfilUpdateSerializer(perfil, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            self.registrar_bitacora(
                accion=BitacoraAccion.CLIENTE_EDITADO,
                descripcion="Falló la actualización parcial de cliente.",
                modulo=BitacoraModulo.CLIENTES,
                entidad_tipo="Cliente",
                entidad_id=getattr(perfil.usuario, "id_usuario", ""),
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": serializer.errors},
            )
            raise

        snapshot_antes = obtener_snapshot_perfil(perfil)
        perfil = serializer.save()
        perfil = Perfil.objects.select_related("usuario", "usuario__role").get(pk=perfil.pk)
        snapshot_despues = obtener_snapshot_perfil(perfil)
        metadatos_cambios = construir_metadatos_actualizacion_perfil(
            snapshot_antes,
            snapshot_despues,
            serializer.validated_data,
        )

        self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_EDITADO,
            descripcion="Cliente actualizado parcialmente.",
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="Cliente",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos=metadatos_cambios,
        )

        return Response(PerfilSerializer(perfil).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Clientes"],
        responses={204: OpenApiResponse(description="Cliente desactivado.")},
    )
    def delete(self, request, pk):
        if self._is_client_role(request):
            return Response(
                {"detail": "No tienes permisos para desactivar clientes desde este endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        perfil = self.get_object(pk)
        deactivate_user_profile(perfil=perfil)

        self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_DESACTIVADO,
            descripcion="Cliente desactivado.",
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="Cliente",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={"correo_objetivo": getattr(perfil.usuario, "correo", "")},
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ClienteMeView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "MOVIL_MI_PERFIL"

    def get_object(self, request):
        return get_object_or_404(
            Perfil.objects.select_related("usuario", "usuario__role"),
            usuario=request.user,
            usuario__role__nombre=Rol.RolName.CLIENT,
        )

    @extend_schema(
        tags=["Clientes"],
        responses={200: PerfilSerializer},
    )
    def get(self, request):
        perfil = self.get_object(request)
        serializer = PerfilSerializer(perfil)

        self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_CONSULTADO,
            descripcion="Cliente consultó su propio perfil.",
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="Cliente",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Clientes"],
        request=PerfilUpdateSerializer,
        responses={200: PerfilSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def patch(self, request):
        perfil = self.get_object(request)
        serializer = PerfilUpdateSerializer(perfil, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_EDITADO,
                descripcion="Falló la actualización de perfil propio del cliente.",
                modulo=BitacoraModulo.CLIENTES,
                entidad_tipo="Cliente",
                entidad_id=getattr(perfil.usuario, "id_usuario", ""),
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": serializer.errors},
            )
            raise

        snapshot_antes = obtener_snapshot_perfil(perfil)
        perfil = serializer.save()
        perfil = Perfil.objects.select_related("usuario", "usuario__role").get(pk=perfil.pk)
        snapshot_despues = obtener_snapshot_perfil(perfil)
        metadatos_cambios = construir_metadatos_actualizacion_perfil(
            snapshot_antes,
            snapshot_despues,
            serializer.validated_data,
        )

        self.registrar_bitacora(
            accion=BitacoraAccion.CLIENTE_EDITADO,
            descripcion="Cliente actualizó su propio perfil.",
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="Cliente",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos=metadatos_cambios,
        )

        return Response(PerfilSerializer(perfil).data, status=status.HTTP_200_OK)
