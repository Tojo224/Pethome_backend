from pathlib import Path
from uuid import uuid4

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status, viewsets
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.GestionClientesyMascotas.models.adopcion import Adopcion
from apps.GestionClientesyMascotas.selectors.adopcion_selector import AdopcionSelector
from apps.GestionClientesyMascotas.serializers.adopcion_serializer import AdopcionSerializer
from apps.GestionClientesyMascotas.services.adopcion_service import AdopcionService


class AdopcionViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = AdopcionSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_MASCOTAS"
    lookup_field = "id_adopcion"
    lookup_url_kwarg = "id_adopcion"

    def _is_admin_or_vet(self):
        user = self.request.user
        role_name = (getattr(getattr(user, "role", None), "nombre", "") or "").upper()
        return getattr(user, "is_superuser", False) or role_name in {
            RoleEnum.ADMIN.value,
            RoleEnum.VETERINARIAN.value,
        }

    def _can_manage(self, adopcion):
        return self._is_admin_or_vet() or adopcion.usuario_id == getattr(
            self.request.user,
            "id_usuario",
            None,
        )

    def get_queryset(self):
        public_only = self.request.query_params.get("publica")
        mine = self.request.query_params.get("mias")
        queryset = AdopcionSelector.filter_adopciones(
            veterinaria_id=self.get_tenant_id(),
            user=self.request.user,
            search=self.request.query_params.get("search") or self.request.query_params.get("nombre"),
            especie_id=self.request.query_params.get("especie_id"),
            estado=self.request.query_params.get("estado_adopcion") or self.request.query_params.get("estado"),
            mine=str(mine).lower() in {"1", "true", "si"},
            public_only=(
                str(public_only).lower() in {"1", "true", "si"}
                or (self.action == "list" and not self._is_admin_or_vet())
            ),
        )
        if self.action in {"retrieve", "update", "partial_update", "destroy"} and not self._is_admin_or_vet():
            queryset = Adopcion.objects.filter(veterinaria_id=self.get_tenant_id()).filter(
                Q(usuario=self.request.user)
                | ~Q(estado_adopcion__in=[Adopcion.ESTADO_INACTIVO, Adopcion.ESTADO_ADOPTADO])
            ).select_related("usuario", "usuario__perfil", "especie", "raza")
        return queryset

    @extend_schema(
        tags=["Adopciones"],
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, required=False),
            OpenApiParameter("especie_id", OpenApiTypes.INT, required=False),
            OpenApiParameter("estado_adopcion", OpenApiTypes.STR, required=False),
            OpenApiParameter("mias", OpenApiTypes.BOOL, required=False),
            OpenApiParameter("publica", OpenApiTypes.BOOL, required=False),
        ],
        responses={200: AdopcionSerializer},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Adopciones"],
        request=AdopcionSerializer,
        responses={201: AdopcionSerializer, 400: OpenApiResponse(description="Datos invalidos.")},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            raise

        adopcion = AdopcionService.crear_adopcion(
            veterinaria_id=self.get_tenant_id(),
            usuario=serializer.validated_data.pop("usuario"),
            **serializer.validated_data,
        )
        output = self.get_serializer(adopcion)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        tags=["Adopciones"],
        request=AdopcionSerializer,
        responses={200: AdopcionSerializer, 403: OpenApiResponse(description="Sin permiso.")},
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if not self._can_manage(instance):
            raise PermissionDenied("No puedes modificar publicaciones de otros usuarios.")

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        adopcion = AdopcionService.actualizar_adopcion(instance, **serializer.validated_data)
        return Response(self.get_serializer(adopcion).data)

    @extend_schema(tags=["Adopciones"], request=AdopcionSerializer)
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        tags=["Adopciones"],
        responses={204: OpenApiResponse(description="Desactivado.")},
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_manage(instance):
            raise PermissionDenied("No puedes eliminar publicaciones de otros usuarios.")
        AdopcionService.desactivar_adopcion(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["Adopciones"],
        responses={201: OpenApiResponse(description="Foto subida correctamente.")},
    )
    @action(detail=False, methods=["post"], url_path="upload-foto")
    def upload_foto(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "Debe enviar un archivo en el campo 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_ext = {".jpg", ".jpeg", ".png", ".webp"}
        ext = Path(file.name).suffix.lower()
        if ext not in allowed_ext:
            return Response(
                {"detail": "Formato no permitido. Use JPG, PNG o WEBP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_size_bytes = 5 * 1024 * 1024
        if file.size > max_size_bytes:
            return Response(
                {"detail": "La imagen supera el tamano maximo permitido (5MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant_id = self.get_tenant_id()
        ts = timezone.now().strftime("%Y%m%d%H%M%S")
        safe_name = f"{ts}_{uuid4().hex}{ext}"
        relative_path = f"vet_{tenant_id}/adopciones/{safe_name}"
        stored_path = default_storage.save(relative_path, file)
        file_url = default_storage.url(stored_path)

        return Response(
            {
                "url": file_url,
                "path": stored_path,
            },
            status=status.HTTP_201_CREATED,
        )
