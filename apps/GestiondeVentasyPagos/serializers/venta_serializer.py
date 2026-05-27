from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.GestionClientesyMascotas.models import Mascota
from apps.GestionInventarioProveedores.models import Producto
from apps.GestionServiciosyReserva.models import PrecioServicio, Servicio
from apps.GestiondeVentasyPagos.models import DetalleVenta, Venta

User = get_user_model()


class DetalleVentaCreateSerializer(serializers.Serializer):
    tipo_item = serializers.ChoiceField(choices=DetalleVenta.TipoItem.choices)
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
    cantidad = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    observacion = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class VentaCreateSerializer(serializers.Serializer):
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    mascota = serializers.PrimaryKeyRelatedField(
        queryset=Mascota.objects.all(),
        required=False,
        allow_null=True,
    )
    observacion = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    detalles = DetalleVentaCreateSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        detalles = attrs.get("detalles", [])
        if not detalles:
            raise serializers.ValidationError({"detalles": "Debes registrar al menos un detalle."})
        return attrs


class DetalleVentaReadSerializer(serializers.ModelSerializer):
    id_producto = serializers.IntegerField(source="producto_id", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True, allow_null=True)
    id_servicio = serializers.IntegerField(source="servicio_id", read_only=True)
    servicio_nombre = serializers.CharField(source="servicio.nombre", read_only=True, allow_null=True)
    id_precio_servicio = serializers.IntegerField(source="precio_servicio_id", read_only=True)
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    precio_unitario = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DetalleVenta
        fields = [
            "id_detalle_venta",
            "tipo_item",
            "id_producto",
            "producto_nombre",
            "id_servicio",
            "servicio_nombre",
            "id_precio_servicio",
            "descripcion_item",
            "cantidad",
            "precio_unitario",
            "subtotal",
            "observacion",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]


class VentaListSerializer(serializers.ModelSerializer):
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)
    id_usuario_responsable = serializers.IntegerField(source="usuario_responsable_id", read_only=True)
    usuario_responsable_correo = serializers.CharField(source="usuario_responsable.correo", read_only=True)
    id_cliente = serializers.IntegerField(source="cliente_id", read_only=True)
    cliente_correo = serializers.CharField(source="cliente.correo", read_only=True, allow_null=True)
    id_mascota = serializers.IntegerField(source="mascota_id", read_only=True)
    mascota_nombre = serializers.CharField(source="mascota.nombre", read_only=True, allow_null=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Venta
        fields = [
            "id_venta",
            "fecha_venta",
            "estado_venta",
            "id_veterinaria",
            "id_usuario_responsable",
            "usuario_responsable_correo",
            "id_cliente",
            "cliente_correo",
            "id_mascota",
            "mascota_nombre",
            "subtotal",
            "total",
            "total_items",
            "observacion",
            "estado",
        ]


class VentaDetailSerializer(serializers.ModelSerializer):
    id_veterinaria = serializers.IntegerField(source="veterinaria_id", read_only=True)
    id_usuario_responsable = serializers.IntegerField(source="usuario_responsable_id", read_only=True)
    usuario_responsable_correo = serializers.CharField(source="usuario_responsable.correo", read_only=True)
    id_cliente = serializers.IntegerField(source="cliente_id", read_only=True)
    cliente_correo = serializers.CharField(source="cliente.correo", read_only=True, allow_null=True)
    id_mascota = serializers.IntegerField(source="mascota_id", read_only=True)
    mascota_nombre = serializers.CharField(source="mascota.nombre", read_only=True, allow_null=True)
    detalles = DetalleVentaReadSerializer(many=True, read_only=True)

    class Meta:
        model = Venta
        fields = [
            "id_venta",
            "fecha_venta",
            "estado_venta",
            "id_veterinaria",
            "id_usuario_responsable",
            "usuario_responsable_correo",
            "id_cliente",
            "cliente_correo",
            "id_mascota",
            "mascota_nombre",
            "subtotal",
            "total",
            "observacion",
            "estado",
            "detalles",
        ]
