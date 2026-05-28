from decimal import Decimal

from rest_framework import serializers

from apps.GestionClientesyMascotas.models import Mascota
from apps.GestionInventarioProveedores.models import Producto
from apps.GestionServiciosyReserva.models import PrecioServicio, Servicio
from apps.GestiondeVentasyPagos.models import CarritoTemporal, DetalleCarritoTemporal


class DetalleCarritoReadSerializer(serializers.ModelSerializer):
    producto = serializers.IntegerField(source="producto_id", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True, allow_null=True)
    servicio = serializers.IntegerField(source="servicio_id", read_only=True)
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True, allow_null=True)
    precio_servicio = serializers.IntegerField(source="precio_servicio_id", read_only=True)
    mascota = serializers.IntegerField(source="mascota_id", read_only=True)
    mascota_nombre = serializers.CharField(source="mascota.nombre", read_only=True, allow_null=True)

    class Meta:
        model = DetalleCarritoTemporal
        fields = [
            "id_detalle_carrito",
            "tipo_item",
            "producto",
            "producto_nombre",
            "servicio",
            "servicio_nombre",
            "precio_servicio",
            "mascota",
            "mascota_nombre",
            "descripcion_item",
            "cantidad",
            "precio_unitario_estimado",
            "subtotal_estimado",
            "observacion",
        ]


class CarritoReadSerializer(serializers.ModelSerializer):
    detalles = serializers.SerializerMethodField()

    class Meta:
        model = CarritoTemporal
        fields = [
            "id_carrito",
            "estado_carrito",
            "subtotal_estimado",
            "total_estimado",
            "fecha_actualizacion",
            "detalles",
        ]

    def get_detalles(self, obj):
        detalles = obj.detalles.filter(estado=True).select_related("producto", "servicio", "precio_servicio", "mascota")
        return DetalleCarritoReadSerializer(detalles, many=True).data


class AgregarItemCarritoSerializer(serializers.Serializer):
    tipo_item = serializers.ChoiceField(choices=DetalleCarritoTemporal.TipoItem.choices)
    producto = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(),
        required=False,
        allow_null=True,
    )
    servicio = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.all(),
        required=False,
        allow_null=True,
    )
    precio_servicio = serializers.PrimaryKeyRelatedField(
        queryset=PrecioServicio.objects.all(),
        required=False,
        allow_null=True,
    )
    mascota = serializers.PrimaryKeyRelatedField(
        queryset=Mascota.objects.all(),
        required=False,
        allow_null=True,
    )
    cantidad = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    observacion = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        cantidad = attrs.get("cantidad")
        if cantidad is not None and cantidad <= 0:
            raise serializers.ValidationError({"cantidad": "La cantidad debe ser mayor a cero."})
        if attrs.get("tipo_item") == DetalleCarritoTemporal.TipoItem.SERVICIO and cantidad is None:
            attrs["cantidad"] = Decimal("1")
        return attrs


class ActualizarItemCarritoSerializer(serializers.Serializer):
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a cero.")
        return value
