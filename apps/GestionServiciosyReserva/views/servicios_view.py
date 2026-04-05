from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Servicio
from ..serializers.servicios_serializer import (
    ServicioSerializer
)


class ServicioListCreateView(APIView):
    def get(self, request):
        servicios = Servicio.objects.all()
        serializer = ServicioSerializer(servicios, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ServicioSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ServicioDetailView(APIView):
    def get(self, request, pk):
        servicio = Servicio.objects.get(pk=pk)
        serializer = ServicioSerializer(servicio)
        return Response(serializer.data)

    def put(self, request, pk):
        servicio = Servicio.objects.get(pk=pk)
        serializer = ServicioSerializer(servicio, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            servicio = Servicio.objects.get(pk=pk)
        except Servicio.DoesNotExist:
            return Response({"error": "Servicio no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        servicio.estado = not servicio.estado 
        servicio.save()

        return Response({
            "message": "Estado actualizado correctamente",
            "estado": servicio.estado
        }, status=status.HTTP_200_OK)

