from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from ..models import ComponenteSistema
from ..serializers.componente_sistema_serializer import ComponenteSistemaSerializer

class ComponenteSistemaListView(generics.ListAPIView):
    serializer_class = ComponenteSistemaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Opcionalmente filtrar por plataforma si se requiere
        plataforma = self.request.query_params.get("plataforma")
        qs = ComponenteSistema.objects.all().order_by("codigo")
        if plataforma:
            qs = qs.filter(plataforma=plataforma)
        return qs

    @extend_schema(
        tags=["RBAC"],
        responses={200: ComponenteSistemaSerializer(many=True)},
        description="Listado de todos los componentes de sistema disponibles para asignar permisos."
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
