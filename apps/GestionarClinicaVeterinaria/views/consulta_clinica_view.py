from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.GestionarClinicaVeterinaria.models import ConsultaClinica, HistorialClinico
from apps.GestionarClinicaVeterinaria.serializers import ConsultaClinicaSerializer


class ConsultaClinicaListCreateView(generics.ListCreateAPIView):
    serializer_class = ConsultaClinicaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        id_historial = self.kwargs["id_historial_clinico"]
        return (
            ConsultaClinica.objects.filter(
                historial_clinico_id=id_historial,
                estado=True,
            )
            .select_related(
                "historial_clinico",
                "historial_clinico__mascota",
                "cita",
                "usuario_veterinario",
                "usuario_veterinario__perfil",
                "receta",
            )
            .prefetch_related(
                "tratamientos",
                "vacunas_aplicadas",
                "archivos_clinicos",
                "receta__detalles",
            )
            .order_by("fecha_consulta", "id_consulta_clinica")
        )

    def perform_create(self, serializer):
        id_historial = self.kwargs["id_historial_clinico"]
        historial = get_object_or_404(
            HistorialClinico,
            pk=id_historial,
            estado=True,
        )
        serializer.save(historial_clinico=historial)


class ConsultaClinicaDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ConsultaClinicaSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "id_consulta_clinica"

    def get_queryset(self):
        return (
            ConsultaClinica.objects.filter(estado=True)
            .select_related(
                "historial_clinico",
                "historial_clinico__mascota",
                "cita",
                "usuario_veterinario",
                "usuario_veterinario__perfil",
                "receta",
            )
            .prefetch_related(
                "tratamientos",
                "vacunas_aplicadas",
                "archivos_clinicos",
                "receta__detalles",
            )
        )