from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.GestionClientesyMascotas.models.mascota import Mascota
from apps.GestionClientesyMascotas.serializers.mascota_serializer import MascotaSerializer


class MascotaViewSet(viewsets.ModelViewSet):
    serializer_class = MascotaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Mascota.objects.select_related(
            "usuario",
            "especie",
            "raza"
        ).all().order_by("-id_mascota")

        nombre = self.request.query_params.get("nombre")
        especie_id = self.request.query_params.get("especie_id")
        raza_id = self.request.query_params.get("raza_id")
        usuario_id = self.request.query_params.get("usuario_id")
        estado = self.request.query_params.get("estado")

        if nombre:
            queryset = queryset.filter(nombre__icontains=nombre)

        if especie_id:
            queryset = queryset.filter(especie_id=especie_id)

        if raza_id:
            queryset = queryset.filter(raza_id=raza_id)

        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        if estado is not None:
            estado_lower = estado.lower()
            if estado_lower in ["true", "1"]:
                queryset = queryset.filter(estado=True)
            elif estado_lower in ["false", "0"]:
                queryset = queryset.filter(estado=False)

        return queryset