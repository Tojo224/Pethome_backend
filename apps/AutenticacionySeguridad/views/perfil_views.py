from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema

from apps.AutenticacionySeguridad.services.perfil_service import deactivate_user_profile, activate_user_profile
from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.selectors.perfil_selector import PerfilSelector
from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService
from apps.AutenticacionySeguridad.utils.audit_utils import (
    obtener_snapshot_perfil,
    construir_metadatos_actualizacion_perfil,
)
from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from ..models import Perfil
from ..permissions.tenant_rbac import HasComponentPermission
from ..serializers.perfil_serializer import (
    PerfilSerializer,
    PerfilCreateSerializer,
    PerfilUpdateSerializer
)

def _registrar_bitacora_seguro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        pass

class UsuarioPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class UsuarioListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_USUARIOS"

    @extend_schema(
        tags=["Usuarios"],
        operation_id="auth_usuarios_list",
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, required=False, description="Filtro de texto."),
            OpenApiParameter("rol", OpenApiTypes.STR, required=False, description="Rol por nombre."),
            OpenApiParameter("estado", OpenApiTypes.STR, required=False, description="true/false"),
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False),
        ],
        responses={200: PerfilSerializer},
    )
    def get(self, request):
        vet_id = self.get_tenant_id()
        queryset = PerfilSelector.filter_perfiles(
            veterinaria_id=vet_id,
            search=request.query_params.get("search"),
            rol=request.query_params.get("rol"),
            estado=request.query_params.get("estado"),
        )

        paginator = UsuarioPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PerfilSerializer(page, many=True)

        self.registrar_bitacora(
            accion=BitacoraAccion.USUARIO_CONSULTADO,
            descripcion="Listado de usuarios consultado desde administración.",
            modulo=BitacoraModulo.GESTION_USUARIOS,
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "total": queryset.count(),
                "search": request.query_params.get("search", "").strip(),
                "rol": request.query_params.get("rol"),
                "estado": request.query_params.get("estado"),
            },
        )

        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["Usuarios"],
        request=PerfilCreateSerializer,
        responses={201: PerfilSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def post(self, request):
        serializer = PerfilCreateSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            self.registrar_bitacora(
                accion=BitacoraAccion.USUARIO_CREADO,
                descripcion="Falló la creación de usuario desde administración.",
                modulo=BitacoraModulo.GESTION_USUARIOS,
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": serializer.errors},
            )
            raise

        perfil = serializer.save()

        self.registrar_bitacora(
            accion=BitacoraAccion.USUARIO_CREADO,
            descripcion="Usuario creado desde administración.",
            modulo=BitacoraModulo.GESTION_USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "correo": perfil.usuario.correo,
                "id_rol": getattr(perfil.usuario.role, "id_rol", None),
            },
        )

        return Response(PerfilSerializer(perfil).data, status=status.HTTP_201_CREATED)


class UsuarioClienteListView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_USUARIOS"

    def get_queryset(self):
        vet_id = self.get_tenant_id()
        return PerfilSelector.filter_perfiles(
            veterinaria_id=vet_id,
            rol="CLIENT"
        )

    @extend_schema(
        tags=["Usuarios"],
        operation_id="auth_usuarios_clientes_list",
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, required=False, description="Filtro de texto."),
            OpenApiParameter("estado", OpenApiTypes.STR, required=False, description="true/false"),
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False),
        ],
        responses={200: PerfilSerializer},
    )
    def get(self, request):
        queryset = self.get_queryset()

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search)
                | Q(usuario__correo__icontains=search)
                | Q(telefono__icontains=search)
                | Q(direccion__icontains=search)
            )

        estado = request.query_params.get("estado")
        if estado is not None:
            estado_norm = estado.lower()
            if estado_norm in {"true", "1", "si", "sí"}:
                queryset = queryset.filter(usuario__is_active=True)
            elif estado_norm in {"false", "0", "no"}:
                queryset = queryset.filter(usuario__is_active=False)

        paginator = UsuarioPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PerfilSerializer(page, many=True)

        self.registrar_bitacora(
            accion=BitacoraAccion.USUARIO_CONSULTADO,
            descripcion="Listado de clientes consultado desde administración.",
            modulo=BitacoraModulo.CLIENTES,
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "total": queryset.count(),
                "search": request.query_params.get("search", "").strip(),
                "estado": request.query_params.get("estado"),
            },
        )

        return paginator.get_paginated_response(serializer.data)


class UsuarioDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_USUARIOS"

    def get_object(self, pk):
        perfil = PerfilSelector.get_perfil_with_details(pk, veterinaria_id=self.get_tenant_id())
        if not perfil:
            from django.http import Http404
            raise Http404
        return perfil

    @extend_schema(
        tags=["Usuarios"],
        operation_id="auth_usuarios_retrieve",
        responses={200: PerfilSerializer, 404: OpenApiResponse(description="No encontrado.")},
    )
    def get(self, request, pk):
        perfil = self.get_object(pk)
        serializer = PerfilSerializer(perfil)

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.USUARIO_CONSULTADO,
            descripcion="Detalle de usuario consultado desde administración.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.GESTION_USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={"correo_objetivo": perfil.usuario.correo},
        )

        return Response(serializer.data)

    @extend_schema(
        tags=["Usuarios"],
        request=PerfilUpdateSerializer,
        responses={200: PerfilSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def put(self, request, pk):
        perfil = self.get_object(pk)
        serializer = PerfilUpdateSerializer(perfil, data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            self.registrar_bitacora(
                accion=BitacoraAccion.USUARIO_EDITADO,
                descripcion="Falló la actualización completa de usuario desde administración.",
                modulo=BitacoraModulo.GESTION_USUARIOS,
                entidad_tipo="User",
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
            accion=BitacoraAccion.USUARIO_EDITADO,
            descripcion="Usuario actualizado desde administración.",
            modulo=BitacoraModulo.GESTION_USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos=metadatos_cambios,
        )

        return Response(PerfilSerializer(perfil).data)

    @extend_schema(
        tags=["Usuarios"],
        request=PerfilUpdateSerializer,
        responses={200: PerfilSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def patch(self, request, pk):
        perfil = self.get_object(pk)
        serializer = PerfilUpdateSerializer(perfil, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            self.registrar_bitacora(
                accion=BitacoraAccion.USUARIO_EDITADO,
                descripcion="Falló la actualización parcial de usuario desde administración.",
                modulo=BitacoraModulo.GESTION_USUARIOS,
                entidad_tipo="User",
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
            accion=BitacoraAccion.USUARIO_EDITADO,
            descripcion="Usuario actualizado parcialmente desde administración.",
            modulo=BitacoraModulo.GESTION_USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos=metadatos_cambios,
        )

        return Response(PerfilSerializer(perfil).data)

    @extend_schema(
        tags=["Usuarios"],
        responses={204: OpenApiResponse(description="Usuario desactivado.")},
    )
    def delete(self, request, pk):
        perfil = self.get_object(pk)
        deactivate_user_profile(perfil=perfil)

        self.registrar_bitacora(
            accion=BitacoraAccion.USUARIO_DESACTIVADO,
            descripcion="Usuario desactivado desde administración.",
            modulo=BitacoraModulo.GESTION_USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={"correo_objetivo": perfil.usuario.correo},
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

class UsuarioActivarView(TenantViewMixin, APIView):
    """
    POST /api/auth/usuarios/<int:pk>/activar/
    Reactiva una cuenta de usuario.
    """
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_USUARIOS"

    def post(self, request, pk):
        perfil = PerfilSelector.get_perfil_with_details(pk, veterinaria_id=self.get_tenant_id())
        if not perfil:
            return Response({"error": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)
            
        activate_user_profile(perfil=perfil)

        self.registrar_bitacora(
            accion=BitacoraAccion.USUARIO_ACTIVADO,
            descripcion="Usuario reactivado desde administración.",
            modulo=BitacoraModulo.GESTION_USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={"correo_objetivo": perfil.usuario.correo},
        )

        return Response({"detail": "Usuario activado correctamente."}, status=status.HTTP_200_OK)