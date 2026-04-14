from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)
from apps.AutenticacionySeguridad.permissions.permissions import IsAdminOrClient, IsClientRole
from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService

from ..models import Cita
from ..serializers.citas_serializer import (
    CitaEstadoUpdateSerializer,
    CitaSerializer,
)


def _registrar_bitacora_seguro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        pass


class CitaListCreateView(APIView):
    permission_classes = [IsAdminOrClient]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsClientRole()]
        return super().get_permissions()

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

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.VISUALIZAR,
            descripcion="Listado de citas consultado.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.CITAS,
            entidad_tipo="Cita",
            resultado=BitacoraResultado.EXITO,
            metadatos={"total": citas.count()},
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = CitaSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            cita = serializer.save()

            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.CREAR,
                descripcion="Cita creada.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.CITAS,
                entidad_tipo="Cita",
                entidad_id=getattr(cita, "id_cita", ""),
                resultado=BitacoraResultado.EXITO,
                metadatos={
                    "mascota_id": getattr(cita, "mascota_id", None),
                    "servicio_id": getattr(cita, "servicio_id", None),
                    "modalidad": getattr(cita, "modalidad", None),
                },
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.CREAR,
            descripcion="Falló la creación de cita.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.CITAS,
            entidad_tipo="Cita",
            resultado=BitacoraResultado.FALLO,
            metadatos={"errores": serializer.errors},
        )
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
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.VISUALIZAR,
                descripcion="Falló la consulta de cita: no encontrada o sin acceso.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.CITAS,
                entidad_tipo="Cita",
                entidad_id=pk,
                resultado=BitacoraResultado.FALLO,
            )
            return Response(
                {"error": "Cita no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = CitaSerializer(cita)

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.VISUALIZAR,
            descripcion="Detalle de cita consultado.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.CITAS,
            entidad_tipo="Cita",
            entidad_id=getattr(cita, "id_cita", pk),
            resultado=BitacoraResultado.EXITO,
        )

        return Response(serializer.data)

    def put(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.ACTUALIZAR,
                descripcion="Falló la actualización de cita: no encontrada o sin acceso.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.CITAS,
                entidad_tipo="Cita",
                entidad_id=pk,
                resultado=BitacoraResultado.FALLO,
            )
            return Response(
                {"error": "Cita no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CitaSerializer(cita, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()

            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.ACTUALIZAR,
                descripcion="Cita actualizada.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.CITAS,
                entidad_tipo="Cita",
                entidad_id=getattr(cita, "id_cita", pk),
                resultado=BitacoraResultado.EXITO,
            )

            return Response(serializer.data)

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.ACTUALIZAR,
            descripcion="Falló la actualización de cita por validación.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.CITAS,
            entidad_tipo="Cita",
            entidad_id=getattr(cita, "id_cita", pk),
            resultado=BitacoraResultado.FALLO,
            metadatos={"errores": serializer.errors},
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        cita = self.get_object(request, pk)
        if not cita:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.DESACTIVAR,
                descripcion="Falló el cambio de estado de cita: no encontrada o sin acceso.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.CITAS,
                entidad_tipo="Cita",
                entidad_id=pk,
                resultado=BitacoraResultado.FALLO,
            )
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

        accion = BitacoraAccion.ACTIVAR if cita.estado == Cita.EstadoChoices.PENDIENTE else BitacoraAccion.DESACTIVAR
        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=accion,
            descripcion="Estado de cita actualizado.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.CITAS,
            entidad_tipo="Cita",
            entidad_id=getattr(cita, "id_cita", pk),
            resultado=BitacoraResultado.EXITO,
            metadatos={"estado": cita.estado},
        )

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
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.ACTUALIZAR,
                descripcion="Falló la actualización de estado de cita: no encontrada o sin acceso.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.CITAS,
                entidad_tipo="Cita",
                entidad_id=pk,
                resultado=BitacoraResultado.FALLO,
            )
            return Response(
                {"error": "Cita no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CitaEstadoUpdateSerializer(cita, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.ACTUALIZAR,
                descripcion="Estado de cita actualizado por endpoint específico.",
                usuario=request.user,
                request=request,
                modulo=BitacoraModulo.CITAS,
                entidad_tipo="Cita",
                entidad_id=getattr(cita, "id_cita", pk),
                resultado=BitacoraResultado.EXITO,
                metadatos={"estado": getattr(cita, "estado", None)},
            )

            return Response(CitaSerializer(cita).data, status=status.HTTP_200_OK)

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.ACTUALIZAR,
            descripcion="Falló la actualización de estado de cita por validación.",
            usuario=request.user,
            request=request,
            modulo=BitacoraModulo.CITAS,
            entidad_tipo="Cita",
            entidad_id=getattr(cita, "id_cita", pk),
            resultado=BitacoraResultado.FALLO,
            metadatos={"errores": serializer.errors},
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
