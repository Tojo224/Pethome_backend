from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.AutenticacionySeguridad.models import Perfil, Rol
from apps.AutenticacionySeguridad.permissions.permissions import IsAdminRole, IsClientRole
from apps.AutenticacionySeguridad.serializers.perfil_serializer import (
    PerfilSerializer,
    PerfilCreateSerializer,
    PerfilUpdateSerializer,
)
from apps.AutenticacionySeguridad.services.perfil_service import (
    deactivate_user_profile,
)


class ClientePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ClienteListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return (
            Perfil.objects
            .select_related("usuario", "usuario__role")
            .filter(usuario__role__nombre=Rol.RolName.CLIENT)
            .order_by("-id_perfil")
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

        paginator = ClientePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PerfilSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        data = request.data.copy()

        try:
            rol_cliente = Rol.objects.get(nombre=Rol.RolName.CLIENT)
            data["id_rol"] = rol_cliente.pk
        except Rol.DoesNotExist:
            return Response(
                {"detail": "El rol de cliente no está configurado en el sistema."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = PerfilCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        perfil = serializer.save()
        return Response(PerfilSerializer(perfil).data, status=status.HTTP_201_CREATED)


class ClienteDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return (
            Perfil.objects
            .select_related("usuario", "usuario__role")
            .filter(usuario__role__nombre=Rol.RolName.CLIENT)
        )

    def get_object(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get(self, request, pk):
        perfil = self.get_object(pk)
        serializer = PerfilSerializer(perfil)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        perfil = self.get_object(pk)
        serializer = PerfilUpdateSerializer(perfil, data=request.data)
        serializer.is_valid(raise_exception=True)

        perfil = serializer.save()
        return Response(PerfilSerializer(perfil).data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        perfil = self.get_object(pk)
        serializer = PerfilUpdateSerializer(perfil, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        perfil = serializer.save()
        return Response(PerfilSerializer(perfil).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        perfil = self.get_object(pk)
        deactivate_user_profile(perfil=perfil)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClienteMeView(APIView):
    permission_classes = [IsClientRole]

    def get_object(self, request):
        return get_object_or_404(
            Perfil.objects.select_related("usuario", "usuario__role"),
            usuario=request.user,
            usuario__role__nombre=Rol.RolName.CLIENT,
        )

    def get(self, request):
        perfil = self.get_object(request)
        serializer = PerfilSerializer(perfil)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        perfil = self.get_object(request)
        serializer = PerfilUpdateSerializer(perfil, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        perfil = serializer.save()
        return Response(PerfilSerializer(perfil).data, status=status.HTTP_200_OK)