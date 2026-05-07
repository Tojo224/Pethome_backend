from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from ..models.especie import Especie
from ..models.raza import Raza
from ..serializers.especie_raza_serializer import EspecieSerializer, RazaSerializer
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission

class EspecieListCreateView(generics.ListCreateAPIView):
    queryset = Especie.objects.all().order_by("nombre")
    serializer_class = EspecieSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CATALOGOS"

    @extend_schema(tags=["Catalogos"], responses={200: EspecieSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class EspecieDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Especie.objects.all()
    serializer_class = EspecieSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CATALOGOS"

class RazaListCreateView(generics.ListCreateAPIView):
    serializer_class = RazaSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CATALOGOS"

    def get_queryset(self):
        queryset = Raza.objects.all().select_related("especie").order_by("nombre")
        especie_id = self.request.query_params.get("especie_id")
        if especie_id:
            queryset = queryset.filter(especie_id=especie_id)
        return queryset

    @extend_schema(
        tags=["Catalogos"],
        parameters=[
            OpenApiParameter("especie_id", OpenApiTypes.INT, description="Filtrar por ID de especie"),
        ],
        responses={200: RazaSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class RazaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Raza.objects.all()
    serializer_class = RazaSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "CLI_CATALOGOS"
