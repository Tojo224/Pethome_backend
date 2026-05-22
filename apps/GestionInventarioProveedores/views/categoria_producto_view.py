from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.GestionInventarioProveedores.models.categoria_producto import CategoriaProducto
from apps.GestionInventarioProveedores.serializers.categoria_producto_serializer import CategoriaProductoSerializer


class CategoriaProductoViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = CategoriaProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = self.get_tenant_id()

        queryset = CategoriaProducto.objects.select_related("veterinaria").order_by(
            "-id_categoria_producto"
        )

        if tenant_id:
            queryset = queryset.filter(
                Q(veterinaria_id=tenant_id) | Q(productos__veterinaria_id=tenant_id)
            ).distinct()
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
                Q(nombre__icontains=search) | Q(descripcion__icontains=search)
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
