from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.GestionarClinicaVeterinaria.models import ConsultaClinica, Tratamiento
from apps.GestionarClinicaVeterinaria.serializers import TratamientoSerializer


class TratamientoListCreateView(generics.ListCreateAPIView):
    serializer_class = TratamientoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        id_consulta = self.kwargs["id_consulta_clinica"]
        return Tratamiento.objects.filter(
            consulta_clinica_id=id_consulta,
            estado=True,
        ).select_related("consulta_clinica").order_by("-fecha_creacion")

    def perform_create(self, serializer):
        id_consulta = self.kwargs["id_consulta_clinica"]
        consulta = get_object_or_404(
            ConsultaClinica,
            pk=id_consulta,
            estado=True,
        )
        serializer.save(consulta_clinica=consulta)


class TratamientoDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TratamientoSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "id_tratamiento"

    def get_queryset(self):
        return Tratamiento.objects.filter(
            estado=True
        ).select_related("consulta_clinica")

    def perform_destroy(self, instance):
        instance.estado = False
        instance.save(update_fields=["estado"])