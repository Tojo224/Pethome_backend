from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from apps.GestionClientesyMascotas.models.especie import Especie
from apps.GestionClientesyMascotas.serializers.especie_serializer import EspecieSerializer


class EspecieListView(generics.ListAPIView):
    queryset = Especie.objects.all().order_by("nombre")
    serializer_class = EspecieSerializer
    permission_classes = [IsAuthenticated]