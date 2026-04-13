from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from apps.GestionClientesyMascotas.models.raza import Raza
from apps.GestionClientesyMascotas.serializers.raza_serializer import RazaSerializer


class RazaListView(generics.ListAPIView):
    serializer_class = RazaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Raza.objects.select_related("especie").all().order_by("nombre")
        especie_id = self.request.query_params.get("especie_id")

        if especie_id:
            queryset = queryset.filter(especie_id=especie_id)

        return queryset