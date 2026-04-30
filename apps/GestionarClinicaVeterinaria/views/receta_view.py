from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from apps.GestionarClinicaVeterinaria.models import ConsultaClinica, Receta
from apps.GestionarClinicaVeterinaria.serializers import RecetaSerializer


class RecetaPorConsultaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id_consulta_clinica):
        receta = get_object_or_404(
            Receta.objects.select_related("consulta_clinica").prefetch_related("detalles"),
            consulta_clinica_id=id_consulta_clinica,
            estado=True,
        )
        serializer = RecetaSerializer(receta, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, id_consulta_clinica):
        consulta = get_object_or_404(
            ConsultaClinica,
            pk=id_consulta_clinica,
            estado=True,
        )

        if hasattr(consulta, "receta"):
            return Response(
                {"detail": "La consulta clínica ya tiene una receta registrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RecetaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(consulta_clinica=consulta)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RecetaDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RecetaSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "id_receta"

    def get_queryset(self):
        return Receta.objects.filter(
            estado=True
        ).select_related("consulta_clinica").prefetch_related("detalles")

    def perform_destroy(self, instance):
        instance.estado = False
        instance.save(update_fields=["estado"])