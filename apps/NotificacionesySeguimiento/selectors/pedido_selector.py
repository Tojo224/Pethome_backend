from django.db.models import Prefetch, Q

from apps.GestiondeVentasyPagos.models import Pago

from ..models import Pedido, Seguimiento
from ..services.pedido_tracking_service import PedidoTrackingService
from ..permissions import (
    get_user_role_name,
    is_admin_role,
    is_client_role,
    is_receptionist_role,
    is_superadmin_role,
    is_veterinarian_role,
)


class PedidoSelector:
    @staticmethod
    def base_queryset():
        return Pedido.objects.select_related(
            "usuario",
            "usuario__role",
            "usuario__perfil",
            "veterinaria",
            "cita",
            "cita__servicio",
        ).prefetch_related(
            "detalles__producto",
            Prefetch(
                "seguimientos",
                queryset=Seguimiento.objects.select_related("usuario", "cita").order_by("-fecha_hora"),
            ),
            Prefetch(
                "veterinaria__pagos",
                queryset=Pago.objects.filter(
                    tipo_referencia=Pago.TipoReferencia.PEDIDO_MOVIL,
                ).order_by("-fecha_creacion"),
                to_attr="_tenant_payments_for_orders",
            ),
        )

    @staticmethod
    def scope_queryset_for_user(queryset, user):
        role_name = get_user_role_name(user)
        if getattr(user, "is_superuser", False) or is_superadmin_role(role_name):
            return queryset.none()

        tenant_id = getattr(user, "veterinaria_id", None)
        if not tenant_id:
            return queryset.none()

        queryset = queryset.filter(veterinaria_id=tenant_id)

        if is_client_role(role_name):
            return queryset.filter(usuario_id=user.id_usuario)

        if is_admin_role(role_name) or is_receptionist_role(role_name):
            return queryset

        if is_veterinarian_role(role_name):
            related_pedido_ids = (
                Seguimiento.objects.filter(
                    veterinaria_id=tenant_id,
                    cita__consultas_clinicas__usuario_veterinario_id=user.id_usuario,
                )
                .exclude(pedido_id__isnull=True)
                .values_list("pedido_id", flat=True)
                .distinct()
            )
            return queryset.filter(
                Q(id_pedido__in=related_pedido_ids)
                | Q(cita__consultas_clinicas__usuario_veterinario_id=user.id_usuario)
            ).distinct()

        # Rol no identificado: fallback seguro a datos propios.
        return queryset.filter(Q(usuario_id=user.id_usuario))

    @classmethod
    def get_pedidos_for_user(cls, user):
        queryset = cls.base_queryset().order_by("-fecha_pedido")
        return cls.scope_queryset_for_user(queryset, user)

    @classmethod
    def get_pedido_detail_for_user(cls, user, pedido_id):
        queryset = cls.base_queryset()
        scoped = cls.scope_queryset_for_user(queryset, user)
        pedido = scoped.filter(id_pedido=pedido_id).first()
        if pedido is None:
            return None
        cls._attach_payment_cache_to_instance(pedido)
        return pedido

    @classmethod
    def enrich_pedidos(cls, queryset):
        return cls._attach_payment_cache(queryset)

    @classmethod
    def _attach_payment_cache(cls, queryset):
        pedidos = list(queryset)
        for pedido in pedidos:
            cls._attach_payment_cache_to_instance(pedido)
        return pedidos

    @staticmethod
    def _attach_payment_cache_to_instance(pedido):
        PedidoTrackingService.ensure_public_status_tracking(
            pedido=pedido,
            actor=pedido.usuario,
        )
        tenant_payments = getattr(
            getattr(pedido, "veterinaria", None),
            "_tenant_payments_for_orders",
            [],
        )
        pedido._prefetched_payments = [
            pago for pago in tenant_payments if pago.referencia_id == pedido.id_pedido
        ]
