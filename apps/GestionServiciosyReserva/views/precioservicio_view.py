from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import PrecioServicio
from ..serializers.precioservicio_serializer import PrecioServicioSerializer


class PrecioServicioListCreateView(APIView):
    def get(self, request):
        precios = PrecioServicio.objects.all()
        serializer = PrecioServicioSerializer(precios, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PrecioServicioSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PrecioServicioDetailView(APIView):
    def get(self, request, pk):
        precio = PrecioServicio.objects.get(pk=pk)
        serializer = PrecioServicioSerializer(precio)
        return Response(serializer.data)

    def put(self, request, pk):
        precio = PrecioServicio.objects.get(pk=pk)
        serializer = PrecioServicioSerializer(precio, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            precio = PrecioServicio.objects.get(pk=pk)
        except PrecioServicio.DoesNotExist:
            return Response(
                {"error": "Precio no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        precio.estado = not precio.estado  
        precio.save()

        return Response({
            "message": "Estado del precio actualizado correctamente",
            "estado": precio.estado
        }, status=status.HTTP_200_OK)