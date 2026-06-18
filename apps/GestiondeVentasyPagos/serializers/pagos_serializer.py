from rest_framework import serializers
from apps.GestiondeVentasyPagos.models import Pago, ComprobantePago


class PagoCheckoutSerializer(serializers.Serializer):
    tipo_referencia = serializers.ChoiceField(choices=Pago.TipoReferencia.choices)
    referencia_id = serializers.IntegerField()
    metodo_pago = serializers.ChoiceField(choices=[Pago.MetodoPago.STRIPE])
    origen = serializers.ChoiceField(choices=["WEB", "MOBILE"], required=False, default="WEB")


class PagoConfirmarManualSerializer(serializers.Serializer):
    tipo_referencia = serializers.ChoiceField(choices=Pago.TipoReferencia.choices)
    referencia_id = serializers.IntegerField()
    metodo_pago = serializers.ChoiceField(
        choices=[
            Pago.MetodoPago.EFECTIVO,
            Pago.MetodoPago.TRANSFERENCIA,
            Pago.MetodoPago.QR,
            Pago.MetodoPago.ADMINISTRATIVO,
        ]
    )
    observacion = serializers.CharField(required=False, allow_blank=True, default="")


class ComprobantePagoReadSerializer(serializers.ModelSerializer):
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)
    id_pago = serializers.IntegerField(source="pago_id", read_only=True)

    class Meta:
        model = ComprobantePago
        fields = [
            "id_comprobante",
            "id_veterinaria",
            "id_pago",
            "numero_comprobante",
            "tipo_comprobante",
            "monto",
            "metodo_pago",
            "fecha_emision",
            "detalle_items",
            "estado",
            "url_archivo",
        ]


class PagoReadSerializer(serializers.ModelSerializer):
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)
    id_usuario = serializers.IntegerField(source="usuario_id", read_only=True)
    id_cliente = serializers.IntegerField(source="cliente_id", read_only=True)
    comprobante = serializers.SerializerMethodField(read_only=True)
    checkout_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id_pago",
            "id_veterinaria",
            "id_usuario",
            "id_cliente",
            "tipo_referencia",
            "referencia_id",
            "metodo_pago",
            "estado_pago",
            "monto",
            "moneda",
            "stripe_session_id",
            "stripe_payment_intent_id",
            "codigo_transaccion",
            "observacion",
            "fecha_confirmacion",
            "fecha_creacion",
            "comprobante",
            "checkout_url",
        ]

    def get_comprobante(self, obj):
        if hasattr(obj, "comprobante") and obj.comprobante:
            return ComprobantePagoReadSerializer(obj.comprobante).data
        return None

    def get_checkout_url(self, obj):
        if obj.stripe_session_id and obj.estado_pago == Pago.EstadoPago.PENDIENTE:
            return f"https://checkout.stripe.com/c/pay/{obj.stripe_session_id}"
        return None
