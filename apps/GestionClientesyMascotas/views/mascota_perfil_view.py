from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.AutenticacionySeguridad.permissions.permissions import IsClientAdminOrVeterinario
from apps.GestionClientesyMascotas.models.mascota import Mascota
from apps.GestionClientesyMascotas.serializers.mascota_serializer import MascotaSerializer
from apps.GestionarClinicaVeterinaria.models import HistorialClinico
from apps.GestionarClinicaVeterinaria.serializers.historial_clinico_serializer import HistorialClinicoSerializer


class MascotaPerfilView(APIView):
    permission_classes = [IsAuthenticated, IsClientAdminOrVeterinario]

    def get(self, request, id_mascota):
        queryset = Mascota.objects.select_related(
            "usuario",
            "usuario__perfil",
            "especie",
            "raza",
        )

        user = request.user
        rol = user.role.nombre.upper()

        if rol == "CLIENTE":
            mascota = get_object_or_404(
                queryset,
                id_mascota=id_mascota,
                usuario=user,
            )
        else:
            mascota = get_object_or_404(
                queryset,
                id_mascota=id_mascota,
            )

        mascota_data = MascotaSerializer(mascota, context={"request": request}).data
        return Response(mascota_data, status=status.HTTP_200_OK)


class MascotaHistorialClinicoView(APIView):
    permission_classes = [IsAuthenticated, IsClientAdminOrVeterinario]

    def get(self, request, id_mascota):
        queryset = Mascota.objects.select_related(
            "usuario",
            "usuario__perfil",
            "especie",
            "raza",
        )

        user = request.user
        rol = user.role.nombre.upper()

        if rol == "CLIENTE":
            mascota = get_object_or_404(
                queryset,
                id_mascota=id_mascota,
                usuario=user,
            )
        else:
            mascota = get_object_or_404(
                queryset,
                id_mascota=id_mascota,
            )

        historial = HistorialClinico.objects.filter(
            mascota=mascota,
            estado=True
        ).select_related(
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
        ).first()

        if not historial:
            return Response(
                {"detail": "No existe historial clínico para esta mascota."},
                status=status.HTTP_404_NOT_FOUND,
            )

        historial_data = HistorialClinicoSerializer(
            historial,
            context={"request": request}
        ).data

        return Response(
            {"historial_clinico": historial_data},
            status=status.HTTP_200_OK
        )


class MascotasMeView(APIView):
    permission_classes = [IsAuthenticated, IsClientAdminOrVeterinario]

    def get(self, request):
        mascotas = Mascota.objects.select_related(
            "usuario",
            "usuario__perfil",
            "especie",
            "raza",
        ).filter(
            usuario=request.user
        ).order_by("-fecha_registro")

        mascotas_data = MascotaSerializer(
            mascotas,
            many=True,
            context={"request": request}
        ).data

        return Response(
            {"mascotas": mascotas_data},
            status=status.HTTP_200_OK
        )