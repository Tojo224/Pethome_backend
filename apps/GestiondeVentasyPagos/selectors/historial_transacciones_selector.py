from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch, Q
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date

from apps.GestionServiciosyReserva.models import Cita
from apps.GestiondeVentasyPagos.models import Pago, TransaccionPago, Venta
from apps.NotificacionesySeguimiento.models import Pedido


class HistorialTransaccionesSelector:
    SUPPORTED_REFERENCE_TYPES = (
        Pago.TipoReferencia.VENTA_WEB,
        Pago.TipoReferencia.PEDIDO_MOVIL,
        Pago.TipoReferencia.CITA_SERVICIO,
    )

    OPERATION_LABELS = {
        Pago.TipoReferencia.VENTA_WEB: "Venta web",
        Pago.TipoReferencia.PEDIDO_MOVIL: "Pedido movil",
        Pago.TipoReferencia.CITA_SERVICIO: "Cita de servicio",
        Pago.TipoReferencia.SAAS_SUSCRIPCION: "Suscripcion SaaS",
    }

    @classmethod
    def get_historial_queryset(cls, *, veterinaria_id: int, params=None):
        queryset = (
            Pago.objects.select_related(
                "veterinaria",
                "cliente__perfil",
                "usuario__perfil",
                "comprobante",
            )
            .prefetch_related(
                Prefetch(
                    "transacciones",
                    queryset=TransaccionPago.objects.order_by(
                        "-fecha_respuesta",
                        "-fecha_creacion",
                        "-id_transaccion",
                    ),
                )
            )
            .filter(
                veterinaria_id=veterinaria_id,
                tipo_referencia__in=cls.SUPPORTED_REFERENCE_TYPES,
            )
            .annotate(fecha_relevante=Coalesce("fecha_confirmacion", "fecha_creacion"))
            .order_by("-fecha_relevante", "-id_pago")
        )

        if params is None:
            return queryset
        return cls._apply_filters(queryset=queryset, veterinaria_id=veterinaria_id, params=params)

    @classmethod
    def get_historial_detalle(cls, *, veterinaria_id: int, id_pago: int):
        pago = cls.get_historial_queryset(veterinaria_id=veterinaria_id).filter(id_pago=id_pago).first()
        if not pago:
            return None

        cls.enrich_pagos([pago], veterinaria_id=veterinaria_id, include_items=True)
        return pago

    @classmethod
    def enrich_pagos(
        cls,
        pagos: Iterable[Pago],
        *,
        veterinaria_id: int,
        include_items: bool = False,
    ) -> list[Pago]:
        pagos = list(pagos)
        if not pagos:
            return pagos

        referencia_ids_by_type: dict[str, set[int]] = {
            tipo: set() for tipo in cls.SUPPORTED_REFERENCE_TYPES
        }
        for pago in pagos:
            referencia_ids_by_type.setdefault(pago.tipo_referencia, set()).add(pago.referencia_id)

        ventas = cls._get_ventas(veterinaria_id=veterinaria_id, ids=referencia_ids_by_type[Pago.TipoReferencia.VENTA_WEB])
        pedidos = cls._get_pedidos(
            veterinaria_id=veterinaria_id,
            ids=referencia_ids_by_type[Pago.TipoReferencia.PEDIDO_MOVIL],
        )
        citas = cls._get_citas(
            veterinaria_id=veterinaria_id,
            ids=referencia_ids_by_type[Pago.TipoReferencia.CITA_SERVICIO],
        )

        for pago in pagos:
            cls._hydrate_base_fields(pago)

            if pago.tipo_referencia == Pago.TipoReferencia.VENTA_WEB:
                cls._hydrate_from_venta(
                    pago,
                    venta=ventas.get(pago.referencia_id),
                    include_items=include_items,
                )
            elif pago.tipo_referencia == Pago.TipoReferencia.PEDIDO_MOVIL:
                cls._hydrate_from_pedido(
                    pago,
                    pedido=pedidos.get(pago.referencia_id),
                    include_items=include_items,
                )
            elif pago.tipo_referencia == Pago.TipoReferencia.CITA_SERVICIO:
                cls._hydrate_from_cita(
                    pago,
                    cita=citas.get(pago.referencia_id),
                    include_items=include_items,
                )
            else:
                cls._hydrate_missing_reference(pago)

        return pagos

    @classmethod
    def _apply_filters(cls, *, queryset, veterinaria_id: int, params):
        tipo_referencia = params.get("tipo_referencia")
        estado_pago = params.get("estado_pago")
        metodo_pago = params.get("metodo_pago")
        cliente = params.get("cliente")
        estado_referencia = params.get("estado_referencia")
        fecha_inicio = parse_date(params.get("fecha_inicio", ""))
        fecha_fin = parse_date(params.get("fecha_fin", ""))
        monto_min = cls._parse_decimal(params.get("monto_min"))
        monto_max = cls._parse_decimal(params.get("monto_max"))

        if tipo_referencia:
            queryset = queryset.filter(tipo_referencia=tipo_referencia)
        if estado_pago:
            queryset = queryset.filter(estado_pago=estado_pago)
        if metodo_pago:
            queryset = queryset.filter(metodo_pago=metodo_pago)
        if fecha_inicio:
            queryset = queryset.filter(fecha_relevante__date__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_relevante__date__lte=fecha_fin)
        if monto_min is not None:
            queryset = queryset.filter(monto__gte=monto_min)
        if monto_max is not None:
            queryset = queryset.filter(monto__lte=monto_max)
        if cliente:
            queryset = cls._filter_by_cliente(
                queryset=queryset,
                veterinaria_id=veterinaria_id,
                cliente_id=cliente,
            )
        if estado_referencia:
            queryset = cls._filter_by_estado_referencia(
                queryset=queryset,
                veterinaria_id=veterinaria_id,
                estado_referencia=estado_referencia,
            )
        return queryset

    @classmethod
    def _filter_by_cliente(cls, *, queryset, veterinaria_id: int, cliente_id):
        try:
            cliente_id = int(cliente_id)
        except (TypeError, ValueError):
            return queryset.none()

        venta_ids = Venta.objects.filter(
            veterinaria_id=veterinaria_id,
            cliente_id=cliente_id,
        ).values_list("id_venta", flat=True)
        pedido_ids = Pedido.objects.filter(
            veterinaria_id=veterinaria_id,
            usuario_id=cliente_id,
        ).values_list("id_pedido", flat=True)
        cita_ids = Cita.objects.filter(
            veterinaria_id=veterinaria_id,
            usuario_id=cliente_id,
        ).values_list("id_cita", flat=True)

        return queryset.filter(
            Q(tipo_referencia=Pago.TipoReferencia.VENTA_WEB, referencia_id__in=venta_ids)
            | Q(tipo_referencia=Pago.TipoReferencia.PEDIDO_MOVIL, referencia_id__in=pedido_ids)
            | Q(tipo_referencia=Pago.TipoReferencia.CITA_SERVICIO, referencia_id__in=cita_ids)
        )

    @classmethod
    def _filter_by_estado_referencia(cls, *, queryset, veterinaria_id: int, estado_referencia: str):
        venta_ids = Venta.objects.filter(
            veterinaria_id=veterinaria_id,
            estado_venta=estado_referencia,
        ).values_list("id_venta", flat=True)
        pedido_ids = Pedido.objects.filter(
            veterinaria_id=veterinaria_id,
            estado_pedido=estado_referencia,
        ).values_list("id_pedido", flat=True)
        cita_ids = Cita.objects.filter(
            veterinaria_id=veterinaria_id,
            estado=estado_referencia,
        ).values_list("id_cita", flat=True)

        return queryset.filter(
            Q(tipo_referencia=Pago.TipoReferencia.VENTA_WEB, referencia_id__in=venta_ids)
            | Q(tipo_referencia=Pago.TipoReferencia.PEDIDO_MOVIL, referencia_id__in=pedido_ids)
            | Q(tipo_referencia=Pago.TipoReferencia.CITA_SERVICIO, referencia_id__in=cita_ids)
        )

    @staticmethod
    def _parse_decimal(value):
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    @classmethod
    def _get_ventas(cls, *, veterinaria_id: int, ids: set[int]):
        if not ids:
            return {}
        ventas = (
            Venta.objects.select_related(
                "cliente__perfil",
                "veterinaria",
                "mascota",
            )
            .prefetch_related(
                "detalles__producto",
                "detalles__servicio",
                "detalles__precio_servicio",
            )
            .filter(veterinaria_id=veterinaria_id, id_venta__in=ids)
        )
        return {venta.id_venta: venta for venta in ventas}

    @classmethod
    def _get_pedidos(cls, *, veterinaria_id: int, ids: set[int]):
        if not ids:
            return {}
        pedidos = (
            Pedido.objects.select_related(
                "usuario__perfil",
                "veterinaria",
            )
            .prefetch_related("detalles__producto")
            .filter(veterinaria_id=veterinaria_id, id_pedido__in=ids)
        )
        return {pedido.id_pedido: pedido for pedido in pedidos}

    @classmethod
    def _get_citas(cls, *, veterinaria_id: int, ids: set[int]):
        if not ids:
            return {}
        citas = (
            Cita.objects.select_related(
                "usuario__perfil",
                "veterinaria",
                "servicio",
                "precio_servicio",
                "mascota",
            )
            .filter(veterinaria_id=veterinaria_id, id_cita__in=ids)
        )
        return {cita.id_cita: cita for cita in citas}

    @classmethod
    def _hydrate_base_fields(cls, pago: Pago) -> None:
        pago.historial_tipo_operacion_legible = cls.OPERATION_LABELS.get(
            pago.tipo_referencia,
            pago.tipo_referencia,
        )
        pago.historial_fecha_pago = pago.fecha_confirmacion
        pago.historial_tiene_comprobante = cls._get_comprobante(pago) is not None
        pago.historial_id_comprobante = getattr(cls._get_comprobante(pago), "id_comprobante", None)
        pago.historial_comprobante = cls._build_comprobante_payload(cls._get_comprobante(pago))
        pago.historial_veterinaria = cls._build_veterinaria_payload(pago.veterinaria)
        pago.historial_referencia_pasarela = cls._build_gateway_reference(pago)
        pago.historial_items = []
        pago.historial_cliente = None
        pago.historial_cliente_id = None
        pago.historial_cliente_nombre = None
        pago.historial_estado_referencia = None
        pago.historial_concepto = f"Pago {pago.tipo_referencia} #{pago.referencia_id}"
        pago.historial_subtotal = pago.monto
        pago.historial_total = pago.monto
        pago.historial_observaciones = pago.observacion

    @classmethod
    def _hydrate_from_venta(cls, pago: Pago, *, venta: Venta | None, include_items: bool) -> None:
        if not venta:
            cls._hydrate_missing_reference(pago)
            return

        cliente_payload = cls._build_user_payload(
            venta.cliente,
            empty_label="Sin cliente registrado",
        )
        pago.historial_cliente = cliente_payload
        pago.historial_cliente_id = cliente_payload["id"]
        pago.historial_cliente_nombre = cliente_payload["nombre"]
        pago.historial_estado_referencia = venta.estado_venta
        pago.historial_concepto = f"Venta web #{venta.id_venta}"
        pago.historial_subtotal = venta.subtotal
        pago.historial_total = venta.total
        pago.historial_observaciones = venta.observacion or pago.observacion
        if include_items:
            pago.historial_items = [
                {
                    "id": detalle.id_detalle_venta,
                    "tipo": detalle.tipo_item,
                    "descripcion": detalle.descripcion_item,
                    "cantidad": detalle.cantidad,
                    "precio_unitario": detalle.precio_unitario,
                    "subtotal": detalle.subtotal,
                }
                for detalle in venta.detalles.filter(estado=True)
            ]

    @classmethod
    def _hydrate_from_pedido(cls, pago: Pago, *, pedido: Pedido | None, include_items: bool) -> None:
        if not pedido:
            cls._hydrate_missing_reference(pago)
            return

        cliente_base = pago.cliente or pedido.usuario
        cliente_payload = cls._build_user_payload(cliente_base)
        pago.historial_cliente = cliente_payload
        pago.historial_cliente_id = cliente_payload["id"]
        pago.historial_cliente_nombre = cliente_payload["nombre"]
        pago.historial_estado_referencia = pedido.estado_pedido
        pago.historial_concepto = f"Pedido movil #{pedido.id_pedido}"
        pago.historial_subtotal = pedido.subtotal
        pago.historial_total = pedido.total
        pago.historial_observaciones = pedido.observacion or pago.observacion
        if include_items:
            pago.historial_items = [
                {
                    "id": detalle.id_detalle_pedido,
                    "tipo": "PRODUCTO",
                    "descripcion": detalle.producto.nombre,
                    "cantidad": detalle.cantidad,
                    "precio_unitario": detalle.precio_unitario,
                    "subtotal": detalle.subtotal,
                }
                for detalle in pedido.detalles.filter(estado=True)
            ]

    @classmethod
    def _hydrate_from_cita(cls, pago: Pago, *, cita: Cita | None, include_items: bool) -> None:
        if not cita:
            cls._hydrate_missing_reference(pago)
            return

        cliente_payload = cls._build_user_payload(cita.usuario)
        pago.historial_cliente = cliente_payload
        pago.historial_cliente_id = cliente_payload["id"]
        pago.historial_cliente_nombre = cliente_payload["nombre"]
        pago.historial_estado_referencia = cita.estado
        pago.historial_concepto = f"Cita de servicio #{cita.id_cita} - {cita.servicio.nombre}"
        pago.historial_subtotal = cita.precio_servicio.precio
        pago.historial_total = cita.precio_servicio.precio
        pago.historial_observaciones = cita.descripcion or pago.observacion
        if include_items:
            pago.historial_items = [
                {
                    "id": cita.id_cita,
                    "tipo": "SERVICIO",
                    "descripcion": cita.servicio.nombre,
                    "cantidad": 1,
                    "precio_unitario": cita.precio_servicio.precio,
                    "subtotal": cita.precio_servicio.precio,
                }
            ]

    @classmethod
    def _hydrate_missing_reference(cls, pago: Pago) -> None:
        pago.historial_estado_referencia = None
        pago.historial_concepto = f"Referencia no disponible para {pago.tipo_referencia} #{pago.referencia_id}"
        pago.historial_items = []

    @staticmethod
    def _get_comprobante(pago: Pago):
        try:
            return pago.comprobante
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def _build_user_payload(user, *, empty_label=None):
        if not user:
            return {
                "id": None,
                "nombre": empty_label,
                "correo": None,
            }

        perfil = getattr(user, "perfil", None)
        nombre = getattr(perfil, "nombre", None) or user.correo
        return {
            "id": user.id_usuario,
            "nombre": nombre,
            "correo": user.correo,
        }

    @staticmethod
    def _build_veterinaria_payload(veterinaria):
        if not veterinaria:
            return None
        return {
            "id": veterinaria.id_veterinaria,
            "nombre": veterinaria.nombre,
            "correo": veterinaria.correo,
        }

    @staticmethod
    def _build_comprobante_payload(comprobante):
        if not comprobante:
            return None
        return {
            "id_comprobante": comprobante.id_comprobante,
            "numero_comprobante": comprobante.numero_comprobante,
            "tipo_comprobante": comprobante.tipo_comprobante,
            "monto": comprobante.monto,
            "metodo_pago": comprobante.metodo_pago,
            "fecha_emision": comprobante.fecha_emision,
            "estado": comprobante.estado,
            "url_archivo": comprobante.url_archivo,
        }

    @classmethod
    def _build_gateway_reference(cls, pago: Pago):
        latest_tx = next(iter(pago.transacciones.all()), None)
        if latest_tx and latest_tx.provider_reference:
            return latest_tx.provider_reference
        return pago.stripe_payment_intent_id or pago.stripe_session_id
