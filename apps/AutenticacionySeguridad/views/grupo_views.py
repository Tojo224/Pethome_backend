from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema

from ..models import GrupoPermisoComponente, GrupoUsuario
from ..permissions.tenant_rbac import HasComponentPermission
from ..serializers.grupo_serializer import (
    GrupoPermisoComponenteSerializer,
    GrupoUsuarioSerializer,
)
from ..services.bitacora_register_service import BitacoraService
from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from rest_framework.response import Response


def _registrar_bitacora_seguro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        pass


def _tenant_id(request):
    tenant = getattr(request, "tenant", None)
    return getattr(tenant, "id", None)


class GrupoUsuarioListCreateView(generics.ListCreateAPIView):
    serializer_class = GrupoUsuarioSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_GRUPO_USUARIO"

    def get_queryset(self):
        return GrupoUsuario.objects.filter(
            veterinaria_id=_tenant_id(self.request)
        ).order_by("nombre")

    @extend_schema(
        tags=["RBAC"],
        responses={200: GrupoUsuarioSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["RBAC"],
        request=GrupoUsuarioSerializer,
        responses={201: GrupoUsuarioSerializer},
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 201:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.GRUPO_CREADO,
                descripcion=f"Grupo de usuario '{response.data.get('nombre')}' creado.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.ROLES_PERMISOS,
                entidad_tipo="GrupoUsuario",
                entidad_id=response.data.get("id_grupo"),
                resultado=BitacoraResultado.EXITO,
                metadatos=response.data
            )
        return response

    def perform_create(self, serializer):
        serializer.save(veterinaria_id=_tenant_id(self.request))


class GrupoUsuarioDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GrupoUsuarioSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_GRUPO_USUARIO"

    def get_queryset(self):
        return GrupoUsuario.objects.filter(
            veterinaria_id=_tenant_id(self.request)
        )

    @extend_schema(tags=["RBAC"], responses={200: GrupoUsuarioSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["RBAC"], request=GrupoUsuarioSerializer, responses={200: GrupoUsuarioSerializer})
    def put(self, request, *args, **kwargs):
        response = super().put(request, *args, **kwargs)
        if response.status_code == 200:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.GRUPO_EDITADO,
                descripcion=f"Grupo de usuario '{response.data.get('nombre')}' actualizado (PUT).",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.ROLES_PERMISOS,
                entidad_tipo="GrupoUsuario",
                entidad_id=response.data.get("id_grupo"),
                resultado=BitacoraResultado.EXITO,
                metadatos=response.data
            )
        return response

    @extend_schema(tags=["RBAC"], request=GrupoUsuarioSerializer, responses={200: GrupoUsuarioSerializer})
    def patch(self, request, *args, **kwargs):
        response = super().patch(request, *args, **kwargs)
        if response.status_code == 200:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.GRUPO_EDITADO,
                descripcion=f"Grupo de usuario '{response.data.get('nombre')}' actualizado (PATCH).",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.ROLES_PERMISOS,
                entidad_tipo="GrupoUsuario",
                entidad_id=response.data.get("id_grupo"),
                resultado=BitacoraResultado.EXITO,
                metadatos=response.data
            )
        return response

    @extend_schema(tags=["RBAC"], responses={204: None})
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        grupo_id = instance.id_grupo
        nombre = instance.nombre
        response = super().delete(request, *args, **kwargs)
        
        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.GRUPO_DESACTIVADO,
            descripcion=f"Grupo de usuario '{nombre}' desactivado.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.ROLES_PERMISOS,
            entidad_tipo="GrupoUsuario",
            entidad_id=grupo_id,
            resultado=BitacoraResultado.EXITO,
        )
        return response


class GrupoPermisoComponenteListCreateView(generics.ListCreateAPIView):
    serializer_class = GrupoPermisoComponenteSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_PERMISO_COMPONENTE"

    def get_queryset(self):
        tenant_id = _tenant_id(self.request)
        queryset = GrupoPermisoComponente.objects.filter(
            grupo__veterinaria_id=tenant_id
        ).select_related("grupo", "componente")

        grupo_id = self.request.query_params.get("grupo_id")
        if grupo_id:
            queryset = queryset.filter(grupo_id=grupo_id)

        return queryset.order_by("id_permiso_componente")

    @extend_schema(
        tags=["RBAC"],
        parameters=[
            OpenApiParameter("grupo_id", OpenApiTypes.INT, required=False, description="Filtra por grupo."),
        ],
        responses={200: GrupoPermisoComponenteSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["RBAC"],
        request=GrupoPermisoComponenteSerializer,
        responses={201: GrupoPermisoComponenteSerializer},
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 201:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.PERMISO_CREADO,
                descripcion=f"Permiso creado para el grupo ID {response.data.get('grupo')}.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.ROLES_PERMISOS,
                entidad_tipo="GrupoPermisoComponente",
                entidad_id=response.data.get("id_permiso_componente"),
                resultado=BitacoraResultado.EXITO,
                metadatos=response.data
            )
        return response

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class GrupoPermisoComponenteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GrupoPermisoComponenteSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SEG_PERMISO_COMPONENTE"

    def get_queryset(self):
        return GrupoPermisoComponente.objects.filter(
            grupo__veterinaria_id=_tenant_id(self.request)
        ).select_related("grupo", "componente")

    @extend_schema(tags=["RBAC"], responses={200: GrupoPermisoComponenteSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["RBAC"], request=GrupoPermisoComponenteSerializer, responses={200: GrupoPermisoComponenteSerializer})
    def put(self, request, *args, **kwargs):
        response = super().put(request, *args, **kwargs)
        if response.status_code == 200:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.PERMISO_EDITADO,
                descripcion=f"Permiso actualizado para el grupo ID {response.data.get('grupo')}.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.ROLES_PERMISOS,
                entidad_tipo="GrupoPermisoComponente",
                entidad_id=response.data.get("id_permiso_componente"),
                resultado=BitacoraResultado.EXITO,
                metadatos=response.data
            )
        return response

    @extend_schema(tags=["RBAC"], request=GrupoPermisoComponenteSerializer, responses={200: GrupoPermisoComponenteSerializer})
    def patch(self, request, *args, **kwargs):
        response = super().patch(request, *args, **kwargs)
        if response.status_code == 200:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.PERMISO_EDITADO,
                descripcion=f"Permiso actualizado parcialmente para el grupo ID {response.data.get('grupo')}.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.ROLES_PERMISOS,
                entidad_tipo="GrupoPermisoComponente",
                entidad_id=response.data.get("id_permiso_componente"),
                resultado=BitacoraResultado.EXITO,
                metadatos=response.data
            )
        return response

    @extend_schema(tags=["RBAC"], responses={204: None})
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        permiso_id = instance.id_permiso_componente
        grupo_id = instance.grupo_id
        response = super().delete(request, *args, **kwargs)
        
        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.PERMISO_ELIMINADO,
            descripcion=f"Permiso ID {permiso_id} eliminado del grupo ID {grupo_id}.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.AUTENTICACION,
            entidad_tipo="GrupoPermisoComponente",
            entidad_id=permiso_id,
            resultado=BitacoraResultado.EXITO,
        )
        return response

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
