from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.AutenticacionySeguridad.models import Rol
from apps.AutenticacionySeguridad.events.bitacora_events import (
    BitacoraAccion,
    BitacoraModulo,
    BitacoraResultado,
)
from apps.AutenticacionySeguridad.serializers.perfil_serializer import (
    PerfilCreateSerializer,
    PerfilSerializer,
)
from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService


def _registrar_bitacora_seguro(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception:
        pass


class RegisterClienteView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Clientes"],
        request=PerfilCreateSerializer,
        responses={201: PerfilSerializer, 400: OpenApiResponse(description="Datos inválidos.")},
    )
    def post(self, request):
        data = request.data.copy()

        try:
            rol_cliente = Rol.objects.get(nombre=Rol.RolName.CLIENT)
            data["id_rol"] = rol_cliente.pk
        except Rol.DoesNotExist:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.CLIENTE_CREADO,
                descripcion="Falló el registro público de cliente: rol CLIENT no configurado.",
                request=request,
                modulo=BitacoraModulo.CLIENTES,
                entidad_tipo="Cliente",
                resultado=BitacoraResultado.FALLO,
            )
            return Response(
                {"detail": "El rol de cliente no está configurado en el sistema."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = PerfilCreateSerializer(data=data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            _registrar_bitacora_seguro(
                BitacoraService.registrar_evento,
                accion=BitacoraAccion.CLIENTE_CREADO,
                descripcion="Falló el registro público de cliente por errores de validación.",
                request=request,
                modulo=BitacoraModulo.CLIENTES,
                entidad_tipo="Cliente",
                resultado=BitacoraResultado.FALLO,
                metadatos={"errores": serializer.errors, "correo": request.data.get("correo", "")},
            )
            raise

        perfil = serializer.save()

        _registrar_bitacora_seguro(
            BitacoraService.registrar_evento,
            accion=BitacoraAccion.CLIENTE_CREADO,
            descripcion="Registro público de cliente exitoso.",
            usuario=getattr(perfil, "usuario", None),
            request=request,
            modulo=BitacoraModulo.CLIENTES,
            entidad_tipo="Cliente",
            entidad_id=getattr(perfil.usuario, "id_usuario", ""),
            resultado=BitacoraResultado.EXITO,
            metadatos={"correo": getattr(perfil.usuario, "correo", "")},
        )

        return Response(PerfilSerializer(perfil).data, status=status.HTTP_201_CREATED)