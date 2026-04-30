from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.GestionarClinicaVeterinaria.models import ArchivoClinico, ConsultaClinica
from apps.GestionarClinicaVeterinaria.serializers.archivo_clinico_serializer import (
    ArchivoClinicoSerializer,
)


class ArchivoClinicoCreateView(generics.CreateAPIView):
    serializer_class = ArchivoClinicoSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        consulta = get_object_or_404(
            ConsultaClinica,
            pk=kwargs["id_consulta_clinica"]
        )

        data = request.data.copy()
        data["consulta_clinica"] = consulta.pk

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        from rest_framework.response import Response
        from rest_framework import status

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ArchivoClinicoUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = ArchivoClinicoSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    queryset = ArchivoClinico.objects.all()
    lookup_field = "id_archivo_clinico"

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)