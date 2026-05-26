from rest_framework import serializers

from apps.AutenticacionySeguridad.models import Veterinaria
from apps.GestionInventarioProveedores.models import CategoriaProducto, Producto, Proveedor


class EstadoField(serializers.Field):
    def to_representation(self, value):
        return "Activo" if value else "Inactivo"

    def to_internal_value(self, data):
        if isinstance(data, bool):
            return data

        if isinstance(data, str):
            value = data.strip().lower()
            if value in ("activo", "true", "1", "si", "sí"):
                return True
            if value in ("inactivo", "false", "0", "no"):
                return False

        raise serializers.ValidationError("Valor de estado inválido")


class ProductoSerializer(serializers.ModelSerializer):
    id_categoria_producto = serializers.PrimaryKeyRelatedField(
        source="categoria_producto",
        queryset=CategoriaProducto.objects.all(),
    )
    id_proveedor = serializers.PrimaryKeyRelatedField(
        source="proveedor",
        queryset=Proveedor.objects.all(),
        required=False,
        allow_null=True,
    )
    id_veterinaria = serializers.PrimaryKeyRelatedField(
        source="veterinaria",
        queryset=Veterinaria.objects.all(),
        required=False,
    )
    estado = EstadoField()
    categoria_nombre = serializers.CharField(
        source="categoria_producto.nombre",
        read_only=True,
    )
    proveedor_nombre = serializers.CharField(
        source="proveedor.nombre",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Producto
        fields = [
            "id_producto",
            "nombre",
            "descripcion",
            "precio_compra",
            "precio_venta",
            "unidad_medida",
            "imagen",
            "visible_catalogo",
            "estado",
            "tipo_mascota",
            "destacado",
            "novedad_desde",
            "novedad_hasta",
            "tiene_promocion",
            "tipo_descuento",
            "porcentaje_descuento",
            "monto_descuento",
            "precio_promocional",
            "promocion_fecha_inicio",
            "promocion_fecha_fin",
            "categoria_nombre",
            "proveedor_nombre",
            "id_categoria_producto",
            "id_proveedor",
            "id_veterinaria",
        ]
        read_only_fields = ["id_producto"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = getattr(self, "instance", None)
        categoria = attrs.get("categoria_producto") or getattr(instance, "categoria_producto", None)
        nombre = (attrs.get("nombre") or getattr(instance, "nombre", "") or "").strip()
        veterinaria = attrs.get("veterinaria") or getattr(instance, "veterinaria", None)

        precio_compra = attrs.get("precio_compra")
        if precio_compra is None and instance is not None:
            precio_compra = getattr(instance, "precio_compra", None)

        precio_venta = attrs.get("precio_venta")
        if precio_venta is None and instance is not None:
            precio_venta = getattr(instance, "precio_venta", None)

        if precio_compra is not None and precio_compra <= 0:
            raise serializers.ValidationError({"precio_compra": "El precio de compra debe ser mayor a 0."})

        if precio_venta is None or precio_venta <= 0:
            raise serializers.ValidationError({"precio_venta": "El precio de venta debe ser mayor a 0."})

        if precio_compra is not None and precio_venta is not None and precio_venta < precio_compra:
            raise serializers.ValidationError({"precio_venta": "El precio de venta no puede ser menor que el precio de compra."})

        if attrs.get("tiene_promocion") or getattr(instance, "tiene_promocion", False):
            precio_promocional = attrs.get("precio_promocional")
            if precio_promocional is None and instance is not None:
                precio_promocional = getattr(instance, "precio_promocional", None)

            porcentaje_descuento = attrs.get("porcentaje_descuento")
            if porcentaje_descuento is None and instance is not None:
                porcentaje_descuento = getattr(instance, "porcentaje_descuento", None)

            monto_descuento = attrs.get("monto_descuento")
            if monto_descuento is None and instance is not None:
                monto_descuento = getattr(instance, "monto_descuento", None)

            tipo_descuento = attrs.get("tipo_descuento")
            if tipo_descuento is None and instance is not None:
                tipo_descuento = getattr(instance, "tipo_descuento", None)

            if tipo_descuento == Producto.TipoDescuento.PRECIO_ESPECIAL:
                if precio_promocional is None or precio_promocional <= 0:
                    raise serializers.ValidationError({"precio_promocional": "El precio promocional debe ser mayor a 0."})
                if precio_promocional >= precio_venta:
                    raise serializers.ValidationError({"precio_promocional": "El precio promocional debe ser menor que el precio de venta."})

            if tipo_descuento == Producto.TipoDescuento.PORCENTAJE and porcentaje_descuento is not None:
                if porcentaje_descuento <= 0 or porcentaje_descuento >= 100:
                    raise serializers.ValidationError({"porcentaje_descuento": "El porcentaje de descuento debe estar entre 0 y 100."})

            if tipo_descuento == Producto.TipoDescuento.MONTO_FIJO and monto_descuento is not None:
                if monto_descuento <= 0 or monto_descuento >= precio_venta:
                    raise serializers.ValidationError({"monto_descuento": "El descuento debe ser mayor a 0 y menor que el precio de venta."})

        if veterinaria and categoria and nombre:
            queryset = Producto.objects.filter(
                veterinaria=veterinaria,
                categoria_producto=categoria,
                nombre__iexact=nombre,
            )

            if instance is not None:
                queryset = queryset.exclude(pk=instance.pk)

            if queryset.exists():
                categoria_nombre = getattr(categoria, "nombre", "la categoría seleccionada")
                proveedor = attrs.get("proveedor") or getattr(instance, "proveedor", None)
                proveedor_nombre = None
                if proveedor is not None:
                    proveedor_nombre = getattr(proveedor, "nombre", None)

                if proveedor_nombre:
                    mensaje = (
                        f"Ya existe un producto con ese nombre, categoría y proveedor en esta veterinaria. "
                        f"Categoría: {categoria_nombre}. Proveedor: {proveedor_nombre}."
                    )
                else:
                    mensaje = (
                        f"Ya existe un producto con ese nombre y categoría en esta veterinaria. "
                        f"Categoría: {categoria_nombre}."
                    )

                raise serializers.ValidationError(
                    {"nombre": mensaje}
                )

        return attrs
