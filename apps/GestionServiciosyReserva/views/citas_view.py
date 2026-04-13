from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.permissions.permissions import IsAdminOrClient

from ..models import Cita
from ..serializers.citas_serializer import (
    CitaEstadoUpdateSerializer,
    CitaSerializer,
)


class CitaListCreateView(APIView):
    permission_classes = [IsAdminOrClient]

    def get_queryset(self, request):
        queryset = (
            Cita.objects.select_related(
                "usuario",
                "mascota",
                "servicio",
                "precio_servicio",
            )
            .order_by("-id_cita")
        )

        if request.user.role.nombre == RoleEnum.CLIENT.value:
            queryset = queryset.filter(usuario=request.user)

        return queryset

    def get(self, request):
        citas = self.get_queryset(request)
        serializer = CitaSerializer(citas, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CitaSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CitaDetailView(APIView):
    permission_classes = [IsAdminOrClient]

    def get_object(self, request, pk):
        try:
            cita = Cita.objects.select_related(
                "usuario",
                "mascota",
                "servicio",
                "precio_servicio",
            ).get(pk=pk)
        except Cita.DoesNotExist:
            return None

        if request.user.role.nombre == RoleEnum.CLIENT.value and cita.usuario_id != request.user.id_usuario:
            return None

        return cita

    def get(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            return Response(
                {"error": "Cita no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CitaSerializer(cita)
        return Response(serializer.data)

    def put(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            return Response(
                {"error": "Cita no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CitaSerializer(cita, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            return Response(
                {"error": "Cita no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cita.estado = (
            Cita.EstadoChoices.PENDIENTE
            if cita.estado == Cita.EstadoChoices.CANCELADA
            else Cita.EstadoChoices.CANCELADA
        )
        cita.save(update_fields=["estado"])

        return Response(
            {
                "message": "Estado de la cita actualizado correctamente",
                "estado": cita.estado,
            },
            status=status.HTTP_200_OK,
        )


class CitaEstadoUpdateView(APIView):
    permission_classes = [IsAdminOrClient]

    def get_object(self, request, pk):
        try:
            cita = Cita.objects.get(pk=pk)
        except Cita.DoesNotExist:
            return None

        if request.user.role.nombre == RoleEnum.CLIENT.value and cita.usuario_id != request.user.id_usuario:
            return None

        return cita

    def patch(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            return Response(
                {"error": "Cita no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CitaEstadoUpdateSerializer(cita, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(CitaSerializer(cita).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
