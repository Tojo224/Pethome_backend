from django.db.models import Q
from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado

from apps.GestionInventarioProveedores.models import Producto
from apps.GestionInventarioProveedores.serializers.producto_serializer import ProductoSerializer


class ProductoViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "INV_PRODUCTOS"
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(tags=["Inventario"], responses={200: ProductoSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        self.registrar_bitacora(
            accion=BitacoraAccion.CATALOGO_CONSULTADO,
            descripcion="Listado de productos consultado.",
            modulo=BitacoraModulo.SISTEMA,
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": self.get_queryset().count()}
        )
        return response

    def get_queryset(self):
        tenant_id = self.get_tenant_id()

        queryset = Producto.objects.select_related(
            "categoria_producto",
            "proveedor",
            "veterinaria",
        ).order_by("-id_producto")

        if tenant_id:
            queryset = queryset.filter(veterinaria_id=tenant_id)
        else:
            queryset = queryset.none()

        estado = self.request.query_params.get("estado")
        search = self.request.query_params.get("search")
        visible_catalogo = self.request.query_params.get("visible_catalogo")
        categoria_producto = self.request.query_params.get("id_categoria_producto")
        proveedor = self.request.query_params.get("id_proveedor")

        if estado is not None:
            if estado.lower() == "true":
                queryset = queryset.filter(estado=True)
            elif estado.lower() == "false":
                queryset = queryset.filter(estado=False)

        if visible_catalogo is not None:
            if visible_catalogo.lower() == "true":
                queryset = queryset.filter(visible_catalogo=True)
            elif visible_catalogo.lower() == "false":
                queryset = queryset.filter(visible_catalogo=False)

        if categoria_producto:
            queryset = queryset.filter(categoria_producto_id=categoria_producto)

        if proveedor:
            queryset = queryset.filter(proveedor_id=proveedor)

        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search)
                | Q(descripcion__icontains=search)
                | Q(unidad_medida__icontains=search)
                | Q(categoria_producto__nombre__icontains=search)
                | Q(proveedor__nombre__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        tenant_id = self.get_tenant_id()
        if not tenant_id:
            raise ValidationError({"detail": "No se pudo resolver la veterinaria actual."})
        serializer.save(veterinaria_id=tenant_id)

    def perform_update(self, serializer):
        tenant_id = self.get_tenant_id()
        if not tenant_id:
            raise ValidationError({"detail": "No se pudo resolver la veterinaria actual."})
        serializer.save(veterinaria_id=tenant_id)


ProductoListView = ProductoViewSet.as_view({
    "get": "list",
    "post": "create",
})
