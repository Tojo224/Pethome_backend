from ..models import Seguimiento


class PedidoTrackingService:
    STATUS_DESCRIPTIONS = {
        "PENDIENTE": "Pedido recibido y pendiente de confirmacion.",
        "CONFIRMADO": "Pago completado y pedido confirmado.",
        "EN_PREPARACION": "Tu pedido esta en preparacion.",
        "EN_CAMINO": "Tu pedido esta en camino.",
        "ENTREGADO": "Tu pedido fue entregado.",
        "CANCELADO": "Tu pedido fue cancelado.",
    }

    @classmethod
    def ensure_public_status_tracking(cls, *, pedido, actor=None):
        latest_public = (
            Seguimiento.objects.filter(
                pedido=pedido,
                tipo_seguimiento="PEDIDO",
                visible_cliente=True,
                estado=True,
            )
            .order_by("-fecha_hora", "-id_seguimiento")
            .first()
        )

        current_status = (pedido.estado_pedido or "").strip().upper()
        if latest_public and (latest_public.estado_actual or "").strip().upper() == current_status:
            return latest_public

        return Seguimiento.objects.create(
            veterinaria_id=pedido.veterinaria_id,
            usuario=actor or pedido.usuario,
            pedido=pedido,
            tipo_seguimiento="PEDIDO",
            estado_anterior=getattr(latest_public, "estado_actual", None),
            estado_actual=current_status,
            descripcion=cls.STATUS_DESCRIPTIONS.get(current_status, "Estado del pedido actualizado."),
            visible_cliente=True,
        )
