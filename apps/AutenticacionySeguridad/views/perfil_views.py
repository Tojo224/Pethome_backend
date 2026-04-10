from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.AutenticacionySeguridad.services.perfil_service import deactivate_user_profile
from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService

from ..events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from ..models import Perfil
from ..permissions.permissions import IsAdminRole
from ..serializers.perfil_serializer import (
    PerfilSerializer,
    PerfilCreateSerializer,
    PerfilUpdateSerializer)


def _registrar_bitacora_seguro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        # No impactar el flujo principal por un error de auditoría.
        pass

class UsuarioPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class UsuarioListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return (
            Perfil.objects
            .select_related("usuario", "usuario__role")
            .all()
            .order_by("-id_perfil")
        )

    def apply_filters(self, queryset, request):
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search)
                | Q(usuario__correo__icontains=search)
                | Q(telefono__icontains=search)
                | Q(direccion__icontains=search)
            )

        rol = request.query_params.get("rol")
        if rol:
            queryset = queryset.filter(usuario__role__nombre=rol)

        estado = request.query_params.get("estado")
        if estado is not None:
            estado_norm = estado.lower()
            if estado_norm in {"true", "1", "si", "sí"}:
                queryset = queryset.filter(usuario__is_active=True)
            elif estado_norm in {"false", "0", "no"}:
                queryset = queryset.filter(usuario__is_active=False)

        return queryset

    def get(self, request):
        queryset = self.apply_filters(self.get_queryset(), request)

        paginator = UsuarioPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PerfilSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = PerfilCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        perfil = serializer.save()

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.CREAR,
            descripcion="Usuario creado desde administración.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "correo": perfil.usuario.correo,
                "id_rol": getattr(perfil.usuario.role, "id_rol", None),
            },
        )

        return Response(PerfilSerializer(perfil).data, status=status.HTTP_201_CREATED)


class UsuarioClienteListView(APIView):
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return Perfil.objects.select_related("usuario", "usuario__role").filter(
            usuario__role__nombre="CLIENT"
        ).order_by("-id_perfil")

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
        return paginator.get_paginated_response(serializer.data)


class UsuarioDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return Perfil.objects.select_related("usuario", "usuario__role")
    
    def get_object(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get(self, request, pk):
        perfil = self.get_object(pk)
        serializer = PerfilSerializer(perfil)
        return Response(serializer.data)

    def put(self, request, pk):
        perfil = self.get_object(pk)
        serializer = PerfilUpdateSerializer(perfil, data=request.data)
        serializer.is_valid(raise_exception=True)

        perfil = serializer.save()

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.ACTUALIZAR,
            descripcion="Usuario actualizado desde administración.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "campos_actualizados": sorted(list(serializer.validated_data.keys())),
                "correo_objetivo": perfil.usuario.correo,
            },
        )

        return Response(PerfilSerializer(perfil).data)

    def patch(self, request, pk):
        perfil = self.get_object(pk)
        serializer = PerfilUpdateSerializer(perfil, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        perfil = serializer.save()

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.ACTUALIZAR,
            descripcion="Usuario actualizado parcialmente desde administración.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "campos_actualizados": sorted(list(serializer.validated_data.keys())),
                "correo_objetivo": perfil.usuario.correo,
            },
        )

        return Response(PerfilSerializer(perfil).data)

    def delete(self, request, pk):
        perfil = self.get_object(pk)
        deactivate_user_profile(perfil=perfil)

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.DESACTIVAR,
            descripcion="Usuario desactivado desde administración.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.USUARIOS,
            entidad_tipo="User",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={"correo_objetivo": perfil.usuario.correo},
        )

        return Response(status=status.HTTP_204_NO_CONTENT)