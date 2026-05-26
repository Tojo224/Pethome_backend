from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.GestionInventarioProveedores.models import PuntoInventario
from apps.GestionInventarioProveedores.serializers.inventario_stock_serializer import PuntoInventarioSerializer


class PuntoInventarioViewSet(TenantViewMixin, viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "INV_PRODUCTOS"

    def list(self, request):
        tenant_id = self.get_tenant_id()
        tipo = request.query_params.get("tipo")
        queryset = PuntoInventario.objects.filter(veterinaria_id=tenant_id).order_by("tipo", "nombre")
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return Response(PuntoInventarioSerializer(queryset, many=True).data)
