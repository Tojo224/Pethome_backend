from django.db import transaction
from rest_framework import serializers
from ..models.producto import Producto

class InventarioService:
    @staticmethod
    @transaction.atomic
    def actualizar_stock(producto_id, cantidad, operacion='SUMA'):
        """
        Actualiza el stock de un producto.
        operacion: 'SUMA' o 'RESTA'
        """
        try:
            producto = Producto.objects.select_for_update().get(pk=producto_id)
        except Producto.DoesNotExist:
            raise serializers.ValidationError({"detail": "Producto no encontrado."})

        if operacion == 'SUMA':
            producto.stock += cantidad
        elif operacion == 'RESTA':
            if producto.stock < cantidad:
                raise serializers.ValidationError({
                    "detail": f"Stock insuficiente para el producto {producto.nombre}. Stock actual: {producto.stock}",
                    "code": "STOCK_INSUFICIENTE"
                })
            producto.stock -= cantidad
        
        producto.save()
        return producto

    @staticmethod
    @transaction.atomic
    def toggle_producto_estado(producto):
        producto.is_active = not producto.is_active
        producto.save()
        return producto

    @staticmethod
    @transaction.atomic
    def toggle_proveedor_estado(proveedor):
        proveedor.is_active = not proveedor.is_active
        proveedor.save()
        return proveedor
