from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.GestionarClinicaVeterinaria.models import DetalleReceta, Receta
from apps.GestionarClinicaVeterinaria.serializers import DetalleRecetaSerializer


class DetalleRecetaListCreateView(generics.ListCreateAPIView):
    serializer_class = DetalleRecetaSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_RECETAS"

    @extend_schema(tags=["Clinica"], responses={200: DetalleRecetaSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Clinica"],
        request=DetalleRecetaSerializer,
        responses={201: DetalleRecetaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        id_receta = self.kwargs["id_receta"]
        tenant = getattr(self.request, "tenant", None)
        vet_id = getattr(tenant, "id", None)
        return DetalleReceta.objects.filter(
            receta_id=id_receta,
            receta__consulta_clinica__veterinaria_id=vet_id,
        ).select_related("receta", "producto").order_by("id_detalle_receta")

    def perform_create(self, serializer):
        id_receta = self.kwargs["id_receta"]
        tenant = getattr(self.request, "tenant", None)
        vet_id = getattr(tenant, "id", None)
        receta = get_object_or_404(
            Receta,
            pk=id_receta,
            consulta_clinica__veterinaria_id=vet_id,
            estado=True,
        )
        serializer.save(receta=receta)


class DetalleRecetaDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DetalleRecetaSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_RECETAS"
    lookup_url_kwarg = "id_detalle_receta"

    @extend_schema(tags=["Clinica"], responses={200: DetalleRecetaSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Clinica"],
        request=DetalleRecetaSerializer,
        responses={200: DetalleRecetaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        tags=["Clinica"],
        request=DetalleRecetaSerializer,
        responses={200: DetalleRecetaSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["Clinica"], responses={204: OpenApiResponse(description="Eliminado.")})
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        vet_id = getattr(tenant, "id", None)
        return DetalleReceta.objects.filter(
            receta__consulta_clinica__veterinaria_id=vet_id
        ).select_related("receta", "producto")

    def perform_destroy(self, instance):
        instance.delete()
