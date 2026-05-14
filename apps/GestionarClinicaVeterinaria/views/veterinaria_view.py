from datetime import date

from django.db.models import Q
from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.AutenticacionySeguridad.models.veterinaria import Veterinaria
from apps.AutenticacionySeguridad.models.plan_suscripcion import PlanSuscripcion
from apps.AutenticacionySeguridad.models.suscripcion import Suscripcion
from apps.AutenticacionySeguridad.services.base_access_seed_service import (
    BaseAccessSeedService,
)
from apps.GestionarClinicaVeterinaria.serializers.veterinaria_serializer import (
    VeterinariaSerializer,
)


class VeterinariaPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class VeterinariaListCreateView(generics.ListCreateAPIView):
    serializer_class = VeterinariaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = VeterinariaPagination

    def _role_name(self):
        role = getattr(self.request.user, "role", None)
        return (getattr(role, "nombre", "") or "").upper()

    def get_queryset(self):
        user = self.request.user
        role_name = self._role_name()
        tenant = getattr(self.request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)

        qs = Veterinaria.objects.all()
        search = (self.request.query_params.get("search") or "").strip()
        estado = self.request.query_params.get("estado")

        if not getattr(user, "is_superuser", False):
            if role_name != "ADMIN":
                raise PermissionDenied("No tienes permisos para listar veterinarias.")
            if not tenant_id:
                return Veterinaria.objects.none()
            qs = qs.filter(id_veterinaria=tenant_id)

        if search:
            qs = qs.filter(
                Q(nombre__icontains=search)
                | Q(slug__icontains=search)
                | Q(correo__icontains=search)
                | Q(telefono__icontains=search)
            )

        if estado in {"true", "false", "1", "0"}:
            qs = qs.filter(estado=estado in {"true", "1"})

        return qs.order_by("-id_veterinaria")

    @extend_schema(
        tags=["Clinica"],
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, required=False),
            OpenApiParameter("estado", OpenApiTypes.BOOL, required=False),
            OpenApiParameter("page", OpenApiTypes.INT, required=False),
            OpenApiParameter("page_size", OpenApiTypes.INT, required=False),
        ],
        responses={200: VeterinariaSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Clinica"], request=VeterinariaSerializer, responses={201: VeterinariaSerializer})
    def post(self, request, *args, **kwargs):
        if not getattr(request.user, "is_superuser", False):
            raise PermissionDenied("Solo superadmin puede crear veterinarias.")
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        vet = serializer.save()
        # Asegura RBAC base por tenant al crear una nueva veterinaria.
        BaseAccessSeedService.seed_global_components()
        BaseAccessSeedService.seed_for_veterinarias(
            veterinarias=[vet],
            assign_existing=False,
        )


class VeterinariaDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = VeterinariaSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id_veterinaria"

    def _role_name(self):
        role = getattr(self.request.user, "role", None)
        return (getattr(role, "nombre", "") or "").upper()

    def get_queryset(self):
        user = self.request.user
        role_name = self._role_name()
        tenant = getattr(self.request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)

        if getattr(user, "is_superuser", False):
            return Veterinaria.objects.all()

        if role_name != "ADMIN":
            raise PermissionDenied("No tienes permisos para consultar veterinarias.")

        if not tenant_id:
            return Veterinaria.objects.none()

        return Veterinaria.objects.filter(id_veterinaria=tenant_id)

    @extend_schema(tags=["Clinica"], responses={200: VeterinariaSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Clinica"], request=VeterinariaSerializer, responses={200: VeterinariaSerializer})
    def put(self, request, *args, **kwargs):
        if not getattr(request.user, "is_superuser", False):
            raise PermissionDenied("Solo superadmin puede editar veterinarias.")
        return super().put(request, *args, **kwargs)

    @extend_schema(tags=["Clinica"], request=VeterinariaSerializer, responses={200: VeterinariaSerializer})
    def patch(self, request, *args, **kwargs):
        if not getattr(request.user, "is_superuser", False):
            raise PermissionDenied("Solo superadmin puede editar veterinarias.")
        return super().patch(request, *args, **kwargs)


class VeterinariaPlanUpdateSerializer(serializers.Serializer):
    id_plan = serializers.IntegerField(required=True)
    estado_suscripcion = serializers.ChoiceField(
        choices=["ACTIVA", "PRUEBA", "VENCIDA", "SUSPENDIDA", "CANCELADA"],
        required=False,
        default="ACTIVA",
    )
    fecha_inicio = serializers.DateField(required=False)
    fecha_fin = serializers.DateField(required=False, allow_null=True)
    renovacion_automatica = serializers.BooleanField(required=False, default=False)


class VeterinariaPlanUpdateView(generics.GenericAPIView):
    serializer_class = VeterinariaPlanUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id_veterinaria"

    def get_queryset(self):
        if not getattr(self.request.user, "is_superuser", False):
            raise PermissionDenied("Solo superadmin puede cambiar planes.")
        return Veterinaria.objects.all()

    @extend_schema(tags=["Clinica"], request=VeterinariaPlanUpdateSerializer, responses={200: VeterinariaSerializer})
    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        vet = self.get_object()
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        plan = PlanSuscripcion.objects.filter(
            id_plan=data["id_plan"],
            estado=True,
        ).first()
        if not plan:
            return Response(
                {"detail": "Plan no encontrado o inactivo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fecha_inicio = data.get("fecha_inicio") or date.today()
        fecha_fin = data.get("fecha_fin")
        if fecha_fin and fecha_fin < fecha_inicio:
            return Response(
                {"detail": "fecha_fin no puede ser menor a fecha_inicio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cerrar suscripciones activas/prueba anteriores para mantener consistencia.
        Suscripcion.objects.filter(
            veterinaria=vet,
            estado_suscripcion__in=["ACTIVA", "PRUEBA"],
        ).exclude(
            estado_suscripcion="CANCELADA",
        ).update(
            estado_suscripcion="CANCELADA",
            fecha_fin=fecha_inicio,
            renovacion_automatica=False,
        )

        Suscripcion.objects.create(
            veterinaria=vet,
            plan=plan,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado_suscripcion=data.get("estado_suscripcion", "ACTIVA"),
            renovacion_automatica=data.get("renovacion_automatica", False),
        )

        response_data = VeterinariaSerializer(vet).data
        return Response(response_data, status=status.HTTP_200_OK)
