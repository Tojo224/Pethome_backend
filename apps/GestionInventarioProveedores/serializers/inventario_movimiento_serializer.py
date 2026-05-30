from decimal import Decimal

from rest_framework import serializers

from apps.GestionInventarioProveedores.models import MovimientoInventario, PuntoInventario, Producto


class MovimientoInventarioCreateSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=MovimientoInventario.TipoMovimiento.choices)
    id_producto = serializers.PrimaryKeyRelatedField(
        source="producto",
        queryset=Producto.objects.all(),
    )
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=2)
    id_punto_origen = serializers.PrimaryKeyRelatedField(
        source="punto_origen",
        queryset=PuntoInventario.objects.all(),
        required=False,
        allow_null=True,
    )
    id_punto_destino = serializers.PrimaryKeyRelatedField(
        source="punto_destino",
        queryset=PuntoInventario.objects.all(),
        required=False,
        allow_null=True,
    )
    motivo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    numero_lote = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=100)
    fecha_vencimiento_lote = serializers.DateField(required=False, allow_null=True)

    def validate_cantidad(self, value: Decimal):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a cero.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tipo = attrs.get("tipo")
        producto = attrs.get("producto")
        numero_lote = attrs.get("numero_lote")
        fecha_vencimiento_lote = attrs.get("fecha_vencimiento_lote")

        if numero_lote:
            attrs["numero_lote"] = numero_lote.strip() or None

        if (
            tipo in {MovimientoInventario.TipoMovimiento.ENTRADA, MovimientoInventario.TipoMovimiento.REPOSICION}
            and producto is not None
            and getattr(producto, "requiere_control_vencimiento", False)
        ):
            if not attrs.get("numero_lote"):
                raise serializers.ValidationError(
                    {"numero_lote": "Este producto requiere número de lote para entradas/reposición."}
                )
            if not fecha_vencimiento_lote:
                raise serializers.ValidationError(
                    {"fecha_vencimiento_lote": "Este producto requiere fecha de vencimiento de lote."}
                )

        return attrs


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    id_producto = serializers.IntegerField(source="producto_id", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    id_usuario = serializers.IntegerField(source="usuario_id", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.nombre", read_only=True)
    id_punto_origen = serializers.IntegerField(source="punto_origen_id", read_only=True)
    punto_origen_nombre = serializers.CharField(source="punto_origen.nombre", read_only=True, allow_null=True)
    id_punto_destino = serializers.IntegerField(source="punto_destino_id", read_only=True)
    punto_destino_nombre = serializers.CharField(source="punto_destino.nombre", read_only=True, allow_null=True)

    class Meta:
        model = MovimientoInventario
        fields = [
            "id_movimiento",
            "tipo",
            "id_producto",
            "producto_nombre",
            "cantidad",
            "numero_lote",
            "fecha_vencimiento_lote",
            "cantidad_anterior",
            "cantidad_posterior",
            "id_usuario",
            "usuario_nombre",
            "id_punto_origen",
            "punto_origen_nombre",
            "id_punto_destino",
            "punto_destino_nombre",
            "motivo",
            "fecha_movimiento",
        ]
