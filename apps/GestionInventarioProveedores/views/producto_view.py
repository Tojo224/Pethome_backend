from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.GestionInventarioProveedores.models import Producto
from apps.GestionInventarioProveedores.serializers.producto_serializer import ProductoSerializer


class ProductoListView(generics.ListAPIView):
    serializer_class = ProductoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Producto.objects.filter(estado=True).order_by("nombre")