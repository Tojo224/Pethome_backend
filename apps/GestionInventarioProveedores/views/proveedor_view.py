from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.GestionInventarioProveedores.models.proveedor import Proveedor
from apps.GestionInventarioProveedores.serializers.proveedor_serializer import ProveedorSerializer


class ProveedorViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = self.get_tenant_id()

        queryset = Proveedor.objects.select_related("veterinaria").order_by("-id_proveedor")

        if tenant_id:
            queryset = queryset.filter(veterinaria_id=tenant_id)
        else:
            queryset = queryset.none()

        estado = self.request.query_params.get("estado")
        search = self.request.query_params.get("search")

        if estado is not None:
            if estado.lower() == "true":
                queryset = queryset.filter(estado=True)
            elif estado.lower() == "false":
                queryset = queryset.filter(estado=False)

        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search)
                | Q(contacto__icontains=search)
                | Q(telefono__icontains=search)
                | Q(ubicacion__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        tenant_id = self.get_tenant_id()
        serializer.save(veterinaria_id=tenant_id)

    def perform_update(self, serializer):
        tenant_id = self.get_tenant_id()
        serializer.save(veterinaria_id=tenant_id)