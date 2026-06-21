from rest_framework import serializers

from apps.GestiondeVentasyPagos.models import Pago


class HistorialClienteSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    nombre = serializers.CharField(allow_null=True, allow_blank=True)
    correo = serializers.EmailField(allow_null=True)


class HistorialVeterinariaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    correo = serializers.EmailField(allow_null=True)


class HistorialComprobanteSerializer(serializers.Serializer):
    id_comprobante = serializers.IntegerField()
    numero_comprobante = serializers.CharField()
    tipo_comprobante = serializers.CharField()
    monto = serializers.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = serializers.CharField()
    fecha_emision = serializers.DateTimeField()
    estado = serializers.CharField()
    url_archivo = serializers.CharField(allow_null=True, allow_blank=True)


class HistorialItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    descripcion = serializers.CharField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)


class HistorialTransaccionListSerializer(serializers.ModelSerializer):
    tipo_operacion_legible = serializers.CharField(source="historial_tipo_operacion_legible", read_only=True)
    fecha_pago = serializers.DateTimeField(source="historial_fecha_pago", read_only=True, allow_null=True)
    cliente_id = serializers.IntegerField(source="historial_cliente_id", read_only=True, allow_null=True)
    cliente_nombre = serializers.CharField(
        source="historial_cliente_nombre",
        read_only=True,
        allow_null=True,
        allow_blank=True,
    )
    concepto = serializers.CharField(source="historial_concepto", read_only=True)
    estado_referencia = serializers.CharField(source="historial_estado_referencia", read_only=True, allow_null=True)
    monto_total = serializers.DecimalField(source="monto", max_digits=12, decimal_places=2, read_only=True)
    referencia_pasarela = serializers.CharField(
        source="historial_referencia_pasarela",
        read_only=True,
        allow_null=True,
        allow_blank=True,
    )
    tiene_comprobante = serializers.BooleanField(source="historial_tiene_comprobante", read_only=True)
    id_comprobante = serializers.IntegerField(source="historial_id_comprobante", read_only=True, allow_null=True)
    veterinaria_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id_pago",
            "tipo_referencia",
            "referencia_id",
            "tipo_operacion_legible",
            "fecha_pago",
            "fecha_creacion",
            "cliente_id",
            "cliente_nombre",
            "concepto",
            "metodo_pago",
            "estado_pago",
            "estado_referencia",
            "monto_total",
            "codigo_transaccion",
            "referencia_pasarela",
            "tiene_comprobante",
            "id_comprobante",
            "veterinaria_id",
        ]


class HistorialTransaccionDetailSerializer(serializers.ModelSerializer):
    fecha_pago = serializers.DateTimeField(source="historial_fecha_pago", read_only=True, allow_null=True)
    cliente = HistorialClienteSerializer(source="historial_cliente", read_only=True, allow_null=True)
    veterinaria = HistorialVeterinariaSerializer(source="historial_veterinaria", read_only=True)
    estado_referencia = serializers.CharField(source="historial_estado_referencia", read_only=True, allow_null=True)
    monto_total = serializers.DecimalField(source="monto", max_digits=12, decimal_places=2, read_only=True)
    referencia_pasarela = serializers.CharField(
        source="historial_referencia_pasarela",
        read_only=True,
        allow_null=True,
        allow_blank=True,
    )
    comprobante = HistorialComprobanteSerializer(source="historial_comprobante", read_only=True, allow_null=True)
    items = HistorialItemSerializer(source="historial_items", many=True, read_only=True)
    subtotal = serializers.DecimalField(source="historial_subtotal", max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(source="historial_total", max_digits=12, decimal_places=2, read_only=True)
    concepto = serializers.CharField(source="historial_concepto", read_only=True)
    observaciones = serializers.CharField(
        source="historial_observaciones",
        read_only=True,
        allow_null=True,
        allow_blank=True,
    )

    class Meta:
        model = Pago
        fields = [
            "id_pago",
            "tipo_referencia",
            "referencia_id",
            "cliente",
            "veterinaria",
            "fecha_pago",
            "fecha_creacion",
            "metodo_pago",
            "estado_pago",
            "estado_referencia",
            "monto_total",
            "codigo_transaccion",
            "referencia_pasarela",
            "comprobante",
            "items",
            "subtotal",
            "total",
            "concepto",
            "observaciones",
        ]
