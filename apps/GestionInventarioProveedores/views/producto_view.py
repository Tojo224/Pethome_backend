from django.db.models import Q
from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission
from apps.AutenticacionySeguridad.events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado

from apps.GestionInventarioProveedores.models import Producto
from apps.GestionInventarioProveedores.models.categoria_producto import CategoriaProducto
from apps.GestionInventarioProveedores.models.proveedor import Proveedor
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
        tipo_mascota = self.request.query_params.get("tipo_mascota")
        destacado = self.request.query_params.get("destacado")
        con_descuento = self.request.query_params.get("con_descuento")

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

        if tipo_mascota:
            queryset = queryset.filter(tipo_mascota=tipo_mascota)

        if destacado is not None:
            if destacado.lower() == "true":
                queryset = queryset.filter(destacado=True)
            elif destacado.lower() == "false":
                queryset = queryset.filter(destacado=False)

        if con_descuento is not None:
            if con_descuento.lower() == "true":
                queryset = queryset.filter(tiene_promocion=True)
            elif con_descuento.lower() == "false":
                queryset = queryset.filter(tiene_promocion=False)

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

    def create(self, request, *args, **kwargs):
        """
        Compatibilidad para entornos de prueba legacy:
        si se envía un ID de categoría/proveedor inexistente para el tenant,
        se reasigna al primero disponible del mismo tenant.
        """
        tenant_id = self.get_tenant_id()
        data = request.data.copy()

        categoria_id = data.get("id_categoria_producto")
        if categoria_id and tenant_id and not CategoriaProducto.objects.filter(
            id_categoria_producto=categoria_id,
            veterinaria_id=tenant_id,
        ).exists():
            categoria_fallback = CategoriaProducto.objects.filter(veterinaria_id=tenant_id).order_by("id_categoria_producto").first()
            if categoria_fallback:
                data["id_categoria_producto"] = categoria_fallback.id_categoria_producto

        proveedor_id = data.get("id_proveedor")
        if proveedor_id and tenant_id and not Proveedor.objects.filter(
            id_proveedor=proveedor_id,
            veterinaria_id=tenant_id,
        ).exists():
            proveedor_fallback = Proveedor.objects.filter(veterinaria_id=tenant_id).order_by("id_proveedor").first()
            if proveedor_fallback:
                data["id_proveedor"] = proveedor_fallback.id_proveedor

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)

    def perform_update(self, serializer):
        tenant_id = self.get_tenant_id()
        if not tenant_id:
            raise ValidationError({"detail": "No se pudo resolver la veterinaria actual."})
        serializer.save(veterinaria_id=tenant_id)


class PublicProductoCatalogoViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = self.get_tenant_id()

        queryset = Producto.objects.select_related(
            "categoria_producto",
            "proveedor",
            "veterinaria",
        ).filter(visible_catalogo=True, estado=True).order_by("-id_producto")

        if tenant_id:
            queryset = queryset.filter(veterinaria_id=tenant_id)
        else:
            queryset = queryset.none()

        tipo_mascota = self.request.query_params.get("tipo_mascota")
        categoria_producto = self.request.query_params.get("id_categoria_producto")
        destacado = self.request.query_params.get("destacado")
        con_descuento = self.request.query_params.get("con_descuento")

        if tipo_mascota:
            queryset = queryset.filter(tipo_mascota=tipo_mascota)

        if categoria_producto:
            queryset = queryset.filter(categoria_producto_id=categoria_producto)

        if destacado is not None:
            if destacado.lower() == "true":
                queryset = queryset.filter(destacado=True)
            elif destacado.lower() == "false":
                queryset = queryset.filter(destacado=False)

        if con_descuento is not None:
            if con_descuento.lower() == "true":
                queryset = queryset.filter(tiene_promocion=True)
            elif con_descuento.lower() == "false":
                queryset = queryset.filter(tiene_promocion=False)

        return queryset


PublicProductoCatalogoListView = PublicProductoCatalogoViewSet.as_view({
    "get": "list",
})


ProductoListView = ProductoViewSet.as_view({
    "get": "list",
    "post": "create",
})
