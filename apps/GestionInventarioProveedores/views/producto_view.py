from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado

from apps.GestionInventarioProveedores.models import Producto
from apps.GestionInventarioProveedores.serializers.producto_serializer import ProductoSerializer


class ProductoListView(TenantViewMixin, generics.ListAPIView):
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "INV_PRODUCTOS"

    @extend_schema(tags=["Inventario"], responses={200: ProductoSerializer})
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.registrar_bitacora(
            accion=BitacoraAccion.CATALOGO_CONSULTADO,
            descripcion="Listado de productos consultado.",
            modulo=BitacoraModulo.SISTEMA,
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": self.get_queryset().count()}
        )
        return response

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        return Producto.objects.filter(
            estado=True,
            veterinaria_id=tenant_id,
        ).order_by("nombre")
