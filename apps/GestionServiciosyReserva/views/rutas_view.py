from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.NotificacionesySeguimiento.permissions import (
    HasVeterinariaOrSuperuser,
    get_user_role_name,
    is_veterinarian_role,
)

from ..models import Cita, DetalleRuta, RutaProgramada, UnidadMovil
from ..serializers import (
    DetalleRutaCreateSerializer,
    DetalleRutaReadSerializer,
    DetalleRutaUpdateSerializer,
    RutaProgramadaReadSerializer,
    RutaProgramadaWriteSerializer,
    UnidadMovilAsignacionReadSerializer,
    UnidadMovilAsignacionWriteSerializer,
    UnidadMovilSerializer,
    UnidadMovilWriteSerializer,
)
from ..models import UnidadMovilAsignacion


def build_ruta_queryset(tenant_id):
    return (
        RutaProgramada.objects.filter(veterinaria_id=tenant_id)
        .select_related(
            "unidad",
            "veterinario",
        )
        .prefetch_related(
            Prefetch(
                "detalles",
                queryset=DetalleRuta.objects.select_related(
                    "cita__servicio",
                    "cita__mascota",
                    "cita__usuario__perfil",
                ).prefetch_related("cita__seguimientos"),
            )
        )
        .annotate(cantidad_citas=Count("detalles"))
        .order_by("fecha", "id_ruta")
    )


def is_admin_like(user):
    role_name = get_user_role_name(user)
    return role_name in {"ADMIN", "SUPERADMIN"}


class UnidadMovilListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get_queryset(self):
        return UnidadMovil.objects.filter(veterinaria_id=self.get_tenant_id()).order_by(
            "nombre",
            "id_unidad",
        )

    def get(self, request):
        serializer = UnidadMovilSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UnidadMovilWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unidad = serializer.save(veterinaria_id=self.get_tenant_id())
        return Response(UnidadMovilSerializer(unidad).data, status=status.HTTP_201_CREATED)


class UnidadMovilDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get_object(self, pk):
        return UnidadMovil.objects.filter(
            pk=pk,
            veterinaria_id=self.get_tenant_id(),
        ).first()

    def get(self, request, pk):
        unidad = self.get_object(pk)
        if unidad is None:
            return Response({"detail": "Unidad movil no encontrada."}, status=404)
        return Response(UnidadMovilSerializer(unidad).data)

    def put(self, request, pk):
        unidad = self.get_object(pk)
        if unidad is None:
            return Response({"detail": "Unidad movil no encontrada."}, status=404)
        serializer = UnidadMovilWriteSerializer(unidad, data=request.data)
        serializer.is_valid(raise_exception=True)
        unidad = serializer.save()
        return Response(UnidadMovilSerializer(unidad).data)

    def patch(self, request, pk):
        unidad = self.get_object(pk)
        if unidad is None:
            return Response({"detail": "Unidad movil no encontrada."}, status=404)
        serializer = UnidadMovilWriteSerializer(unidad, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        unidad = serializer.save()
        return Response(UnidadMovilSerializer(unidad).data)

    def delete(self, request, pk):
        unidad = self.get_object(pk)
        if unidad is None:
            return Response({"detail": "Unidad movil no encontrada."}, status=404)
        unidad.estado = False
        unidad.save(update_fields=["estado"])
        return Response({"detail": "Unidad movil desactivada correctamente."})


class RutaProgramadaListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get_queryset(self, request):
        queryset = build_ruta_queryset(self.get_tenant_id())

        fecha = request.query_params.get("fecha")
        id_veterinario = request.query_params.get("id_veterinario")
        id_unidad = request.query_params.get("id_unidad")
        estado = request.query_params.get("estado")

        if fecha:
            queryset = queryset.filter(fecha=fecha)
        if id_veterinario:
            queryset = queryset.filter(veterinario_id=id_veterinario)
        if id_unidad:
            queryset = queryset.filter(unidad_id=id_unidad)
        if estado:
            queryset = queryset.filter(estado=estado)

        if not is_admin_like(request.user):
            role_name = get_user_role_name(request.user)
            if is_veterinarian_role(role_name):
                queryset = queryset.filter(veterinario=request.user)

        return queryset

    def get(self, request):
        serializer = RutaProgramadaReadSerializer(self.get_queryset(request), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RutaProgramadaWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        ruta = serializer.save()
        ruta = build_ruta_queryset(self.get_tenant_id()).get(pk=ruta.pk)
        return Response(RutaProgramadaReadSerializer(ruta).data, status=status.HTTP_201_CREATED)


class RutaProgramadaDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get_object(self, request, pk):
        queryset = build_ruta_queryset(self.get_tenant_id()).filter(pk=pk)
        if not is_admin_like(request.user):
            role_name = get_user_role_name(request.user)
            if is_veterinarian_role(role_name):
                queryset = queryset.filter(veterinario=request.user)
        return queryset.first()

    def get(self, request, pk):
        ruta = self.get_object(request, pk)
        if ruta is None:
            return Response({"detail": "Ruta programada no encontrada."}, status=404)
        return Response(RutaProgramadaReadSerializer(ruta).data)

    def put(self, request, pk):
        ruta = self.get_object(request, pk)
        if ruta is None:
            return Response({"detail": "Ruta programada no encontrada."}, status=404)
        serializer = RutaProgramadaWriteSerializer(
            ruta,
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        ruta = serializer.save()
        ruta = build_ruta_queryset(self.get_tenant_id()).get(pk=ruta.pk)
        return Response(RutaProgramadaReadSerializer(ruta).data)

    def patch(self, request, pk):
        ruta = self.get_object(request, pk)
        if ruta is None:
            return Response({"detail": "Ruta programada no encontrada."}, status=404)
        serializer = RutaProgramadaWriteSerializer(
            ruta,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        ruta = serializer.save()
        ruta = build_ruta_queryset(self.get_tenant_id()).get(pk=ruta.pk)
        return Response(RutaProgramadaReadSerializer(ruta).data)

    def delete(self, request, pk):
        ruta = self.get_object(request, pk)
        if ruta is None:
            return Response({"detail": "Ruta programada no encontrada."}, status=404)
        ruta.estado = RutaProgramada.EstadoChoices.CANCELADA
        ruta.save(update_fields=["estado"])
        return Response({"detail": "Ruta programada cancelada correctamente."})


class RutaProgramadaDetalleListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get_ruta(self, request, pk):
        queryset = build_ruta_queryset(self.get_tenant_id()).filter(pk=pk)
        if not is_admin_like(request.user):
            role_name = get_user_role_name(request.user)
            if is_veterinarian_role(role_name):
                queryset = queryset.filter(veterinario=request.user)
        return queryset.first()

    def get(self, request, pk):
        ruta = self.get_ruta(request, pk)
        if ruta is None:
            return Response({"detail": "Ruta programada no encontrada."}, status=404)
        detalles = ruta.detalles.all().order_by("orden")
        return Response(DetalleRutaReadSerializer(detalles, many=True).data)

    def post(self, request, pk):
        ruta = self.get_ruta(request, pk)
        if ruta is None:
            return Response({"detail": "Ruta programada no encontrada."}, status=404)
        serializer = DetalleRutaCreateSerializer(
            data=request.data,
            context={"request": request, "ruta": ruta},
        )
        serializer.is_valid(raise_exception=True)
        detalle = serializer.save()
        detalle = (
            DetalleRuta.objects.select_related(
                "cita__servicio",
                "cita__mascota",
                "cita__usuario__perfil",
            )
            .prefetch_related("cita__seguimientos")
            .get(pk=detalle.pk)
        )
        return Response(DetalleRutaReadSerializer(detalle).data, status=status.HTTP_201_CREATED)


class DetalleRutaDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get_object(self, request, pk):
        queryset = (
            DetalleRuta.objects.filter(
                pk=pk,
                ruta__veterinaria_id=self.get_tenant_id(),
            )
            .select_related(
                "ruta",
                "cita__servicio",
                "cita__mascota",
                "cita__usuario__perfil",
            )
            .prefetch_related("cita__seguimientos")
        )
        if not is_admin_like(request.user):
            role_name = get_user_role_name(request.user)
            if is_veterinarian_role(role_name):
                queryset = queryset.filter(ruta__veterinario=request.user)
        return queryset.first()

    def patch(self, request, pk):
        detalle = self.get_object(request, pk)
        if detalle is None:
            return Response({"detail": "Detalle de ruta no encontrado."}, status=404)
        serializer = DetalleRutaUpdateSerializer(
            detalle,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        detalle = serializer.save()
        detalle.refresh_from_db()
        detalle = self.get_object(request, pk)
        return Response(DetalleRutaReadSerializer(detalle).data)

    def delete(self, request, pk):
        detalle = self.get_object(request, pk)
        if detalle is None:
            return Response({"detail": "Detalle de ruta no encontrado."}, status=404)
        detalle.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MisRutasListView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get(self, request):
        fecha = request.query_params.get("fecha") or timezone.localdate().isoformat()
        queryset = build_ruta_queryset(self.get_tenant_id()).filter(fecha=fecha)

        if not is_admin_like(request.user):
            queryset = queryset.filter(veterinario=request.user)

        serializer = RutaProgramadaReadSerializer(queryset, many=True)
        return Response(serializer.data)


class MisRutasHoyView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get(self, request):
        queryset = build_ruta_queryset(self.get_tenant_id()).filter(fecha=timezone.localdate())

        if not is_admin_like(request.user):
            queryset = queryset.filter(veterinario=request.user)

        serializer = RutaProgramadaReadSerializer(queryset, many=True)
        return Response(serializer.data)


class UnidadMovilAsignacionListCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get_queryset(self):
        queryset = (
            UnidadMovilAsignacion.objects.filter(veterinaria_id=self.get_tenant_id())
            .select_related("unidad", "veterinaria")
            .prefetch_related("personal_asignado__usuario__role")
            .order_by("-fecha_inicio", "-id_asignacion")
        )

        id_unidad = self.request.query_params.get("id_unidad")
        fecha = self.request.query_params.get("fecha")
        estado = self.request.query_params.get("estado")

        if id_unidad:
            queryset = queryset.filter(unidad_id=id_unidad)
        if estado is not None:
            normalized = str(estado).strip().lower()
            if normalized in {"true", "1", "activo"}:
                queryset = queryset.filter(estado=True)
            elif normalized in {"false", "0", "inactivo"}:
                queryset = queryset.filter(estado=False)
        if fecha:
            queryset = queryset.filter(
                fecha_inicio__lte=fecha,
            ).filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=fecha))

        return queryset

    def get(self, request):
        serializer = UnidadMovilAsignacionReadSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UnidadMovilAsignacionWriteSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        asignacion = serializer.save()
        asignacion = self.get_queryset().get(pk=asignacion.pk)
        return Response(
            UnidadMovilAsignacionReadSerializer(asignacion).data,
            status=status.HTTP_201_CREATED,
        )


class UnidadMovilAsignacionDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get_object(self, pk):
        return (
            UnidadMovilAsignacion.objects.filter(
                pk=pk,
                veterinaria_id=self.get_tenant_id(),
            )
            .select_related("unidad", "veterinaria")
            .prefetch_related("personal_asignado__usuario__role")
            .first()
        )

    def get(self, request, pk):
        asignacion = self.get_object(pk)
        if asignacion is None:
            return Response({"detail": "Asignacion no encontrada."}, status=404)
        return Response(UnidadMovilAsignacionReadSerializer(asignacion).data)

    def patch(self, request, pk):
        asignacion = self.get_object(pk)
        if asignacion is None:
            return Response({"detail": "Asignacion no encontrada."}, status=404)
        serializer = UnidadMovilAsignacionWriteSerializer(
            asignacion,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        asignacion = serializer.save()
        asignacion = self.get_object(asignacion.pk)
        return Response(UnidadMovilAsignacionReadSerializer(asignacion).data)

    def delete(self, request, pk):
        asignacion = self.get_object(pk)
        if asignacion is None:
            return Response({"detail": "Asignacion no encontrada."}, status=404)
        asignacion.estado = False
        asignacion.save(update_fields=["estado", "updated_at"])
        return Response({"detail": "Asignacion desactivada correctamente."})


class UnidadMovilAsignacionActualView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaOrSuperuser]

    def get(self, request, pk):
        fecha = request.query_params.get("fecha") or timezone.localdate().isoformat()
        asignacion = (
            UnidadMovilAsignacion.objects.filter(
                unidad_id=pk,
                veterinaria_id=self.get_tenant_id(),
                estado=True,
                fecha_inicio__lte=fecha,
            )
            .filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=fecha))
            .select_related("unidad", "veterinaria")
            .prefetch_related("personal_asignado__usuario__role")
            .order_by("-fecha_inicio", "-id_asignacion")
            .first()
        )
        if asignacion is None:
            return Response({"detail": "No existe asignacion activa para esta unidad."}, status=404)
        return Response(UnidadMovilAsignacionReadSerializer(asignacion).data)
