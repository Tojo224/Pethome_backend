from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from apps.GestionInventarioProveedores.models.categoria_producto import CategoriaProducto
from apps.GestionInventarioProveedores.serializers.categoria_producto_serializer import CategoriaProductoSerializer


class CategoriaProductoViewSet(viewsets.ModelViewSet):
    serializer_class = CategoriaProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CategoriaProducto.objects.select_related("veterinaria").order_by(
            "-id_categoria_producto"
        )

        veterinaria_id = self.request.query_params.get("veterinaria_id")
        estado = self.request.query_params.get("estado")
        search = self.request.query_params.get("search")

        if veterinaria_id:
            queryset = queryset.filter(veterinaria_id=veterinaria_id)

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