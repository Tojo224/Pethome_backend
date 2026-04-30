from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.GestionarClinicaVeterinaria.models import HistorialClinico
from apps.GestionarClinicaVeterinaria.serializers.historial_clinico_serializer import (
    HistorialClinicoSerializer,
)


class HistorialClinicoListCreateView(generics.ListCreateAPIView):
    serializer_class = HistorialClinicoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            HistorialClinico.objects.filter(estado=True)
            .select_related(
                "mascota",
                "mascota__usuario",
                "mascota__usuario__perfil",
                "mascota__especie",
                "mascota__raza",
            )
            .prefetch_related(
                "consultas_clinicas",
                "consultas_clinicas__tratamientos",
                "consultas_clinicas__vacunas_aplicadas",
                "consultas_clinicas__archivos_clinicos",
                "consultas_clinicas__receta",
                "consultas_clinicas__receta__detalles",
            )
            .order_by("-fecha_actualizacion", "-id_historial_clinico")
        )


class HistorialClinicoPorMascotaView(generics.RetrieveAPIView):
    serializer_class = HistorialClinicoSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        id_mascota = self.kwargs["id_mascota"]

        return get_object_or_404(
            HistorialClinico.objects.select_related(
                "mascota",
                "mascota__usuario",
                "mascota__usuario__perfil",
                "mascota__especie",
                "mascota__raza",
            ).prefetch_related(
                "consultas_clinicas",
                "consultas_clinicas__tratamientos",
                "consultas_clinicas__vacunas_aplicadas",
                "consultas_clinicas__archivos_clinicos",
                "consultas_clinicas__receta",
                "consultas_clinicas__receta__detalles",
            ),
            mascota_id=id_mascota,
            estado=True,
        )