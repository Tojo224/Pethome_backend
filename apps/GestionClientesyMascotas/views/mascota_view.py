from pathlib import Path
from uuid import uuid4

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema

from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)
from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.GestionClientesyMascotas.selectors.mascota_selector import MascotaSelector
from apps.GestionClientesyMascotas.services.mascota_service import MascotaService
from apps.GestionClientesyMascotas.serializers.mascota_serializer import MascotaSerializer
from apps.GestionClientesyMascotas.serializers.mascota_perfil_serializer import MascotaPerfilSeguimientoSerializer





class MascotaViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = MascotaSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_MASCOTAS"
    lookup_field = "id_mascota"
    lookup_url_kwarg = "id_mascota"



    def get_queryset(self):
        return MascotaSelector.filter_mascotas(
            veterinaria_id=self.get_tenant_id(),
            user=self.request.user,
            search=self.request.query_params.get("nombre"),
            especie_id=self.request.query_params.get("especie_id")
        )

    @extend_schema(
        tags=["Mascotas"],
        parameters=[
            OpenApiParameter("nombre", OpenApiTypes.STR, required=False),
            OpenApiParameter("especie_id", OpenApiTypes.INT, required=False),
            OpenApiParameter("raza_id", OpenApiTypes.INT, required=False),
            OpenApiParameter("usuario_id", OpenApiTypes.INT, required=False),
            OpenApiParameter("estado", OpenApiTypes.STR, required=False, description="true/false"),
        ],
        responses={200: MascotaSerializer},
    )
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        self.registrar_bitacora(
            accion=BitacoraAccion.MASCOTA_CONSULTADA,
            descripcion="Listado de mascotas consultado.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.MASCOTAS,
            entidad_tipo="Mascota",
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "nombre": request.query_params.get("nombre"),
                "especie_id": request.query_params.get("especie_id"),
                "raza_id": request.query_params.get("raza_id"),
                "usuario_id": request.query_params.get("usuario_id"),
                "estado": request.query_params.get("estado"),
            },
        )
        return response

    @extend_schema(
        tags=["Mascotas"],
        responses={200: MascotaSerializer, 404: OpenApiResponse(description="No encontrado.")},
    )
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        self.registrar_bitacora(
            accion=BitacoraAccion.MASCOTA_CONSULTADA,
            descripcion="Detalle de mascota consultado.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.MASCOTAS,
            entidad_tipo="Mascota",
            entidad_id=kwargs.get("pk", ""),
            resultado=BitacoraResultado.EXITO,
        )
        return response

    @extend_schema(
        tags=["Mascotas"],
        request=MascotaSerializer,
        responses={201: MascotaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def create(self, request, *args, **kwargs):
        vet_id = self.get_tenant_id()

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            self.registrar_bitacora(
                accion="MASCOTA_CREADA",
                descripcion="Falló la creación de mascota por errores de validación.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.MASCOTAS,
                entidad_tipo="Mascota",
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": serializer.errors},
            )
            raise

        self.perform_create(serializer)
        data = serializer.data

        self.registrar_bitacora(
            accion=BitacoraAccion.MASCOTA_CREADA,
            descripcion=f"Mascota '{data.get('nombre')}' creada exitosamente.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.MASCOTAS,
            entidad_tipo="Mascota",
            entidad_id=data.get("id_mascota", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={
                "nombre": data.get("nombre"),
                "usuario_id": (request.data or {}).get("usuario_id"),
            },
        )

        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        mascota = MascotaService.crear_mascota(
            veterinaria_id=self.get_tenant_id(),
            usuario=serializer.validated_data.get("usuario"),
            especie=serializer.validated_data.get("especie"),
            raza=serializer.validated_data.get("raza"),
            nombre=serializer.validated_data.get("nombre"),
            sexo=serializer.validated_data.get("sexo"),
            fecha_nac=serializer.validated_data.get("fecha_nac"),
            peso=serializer.validated_data.get("peso"),
            color=serializer.validated_data.get("color"),
            notas_generales=serializer.validated_data.get("notas_generales"),
        )
        serializer.instance = mascota

    @extend_schema(
        tags=["Mascotas"],
        request=MascotaSerializer,
        responses={200: MascotaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            self.registrar_bitacora(
                accion=BitacoraAccion.MASCOTA_EDITADA,
                descripcion="Falló la actualización de mascota por errores de validación.",
                modulo=BitacoraModulo.MASCOTAS,
                entidad_id=getattr(instance, "id_mascota", ""),
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": serializer.errors},
            )
            raise

        self.perform_update(serializer)
        data = serializer.data

        self.registrar_bitacora(
            accion=BitacoraAccion.MASCOTA_EDITADA,
            descripcion="Mascota actualizada." if not partial else "Mascota actualizada parcialmente.",
            modulo=BitacoraModulo.MASCOTAS,
            entidad_id=data.get("id_mascota", getattr(instance, "id_mascota", "")),
            resultado=BitacoraResultado.EXITO,
            metadatos={"campos_actualizados": sorted(list(serializer.validated_data.keys()))},
        )

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return Response(data)

    @extend_schema(
        tags=["Mascotas"],
        request=MascotaSerializer,
        responses={200: MascotaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        tags=["Mascotas"],
        responses={204: OpenApiResponse(description="Eliminado.")},
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        mascota_id = getattr(instance, "id_mascota", "")
        nombre = getattr(instance, "nombre", "")
        self.perform_destroy(instance)

        self.registrar_bitacora(
            accion=BitacoraAccion.MASCOTA_DESACTIVADA,
            descripcion="Mascota eliminada.",
            modulo=BitacoraModulo.MASCOTAS,
            entidad_id=mascota_id,
            resultado=BitacoraResultado.EXITO,
            metadatos={"nombre": nombre},
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["Mascotas"],
        responses={200: MascotaPerfilSeguimientoSerializer},
    )
    @action(detail=True, methods=["get"], url_path="perfil-seguimiento")
    def perfil_seguimiento(self, request, id_mascota=None):
        mascota = self.get_object()
        
        # Auditoría de la consulta
        self.registrar_bitacora(
            accion=BitacoraAccion.PERFIL_MASCOTA_CONSULTADO,
            descripcion=f"Consulta al perfil y seguimiento completo de la mascota '{mascota.nombre}'.",
            modulo=BitacoraModulo.MASCOTAS,
            entidad_id=mascota.id_mascota,
            resultado=BitacoraResultado.EXITO,
        )

        # Registrar también consulta de historial si aplica
        self.registrar_bitacora(
            accion=BitacoraAccion.HISTORIAL_SERVICIOS_CONSULTADO,
            descripcion=f"Consulta al historial de servicios de la mascota '{mascota.nombre}'.",
            modulo=BitacoraModulo.MASCOTAS,
            entidad_id=mascota.id_mascota,
            resultado=BitacoraResultado.EXITO,
        )

        serializer = MascotaPerfilSeguimientoSerializer(mascota, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        tags=["Mascotas"],
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
                {"detail": "La imagen supera el tamaño máximo permitido (5MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant_id = self.get_tenant_id()
        ts = timezone.now().strftime("%Y%m%d%H%M%S")
        safe_name = f"{ts}_{uuid4().hex}{ext}"
        relative_path = f"vet_{tenant_id}/mascotas/{safe_name}"
        stored_path = default_storage.save(relative_path, file)
        file_url = default_storage.url(stored_path)

        return Response(
            {
                "url": file_url,
                "path": stored_path,
            },
            status=status.HTTP_201_CREATED,
        )
