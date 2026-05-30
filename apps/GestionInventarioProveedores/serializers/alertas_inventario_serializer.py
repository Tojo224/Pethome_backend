from django.utils import timezone
from rest_framework import serializers

from ..models import StockPunto


class AlertaInventarioItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    punto_inventario_nombre = serializers.CharField(source="punto_inventario.nombre", read_only=True)
    dias_para_vencer = serializers.SerializerMethodField()

    class Meta:
        model = StockPunto
        fields = [
            "id_stock",
            "producto_nombre",
            "punto_inventario_nombre",
            "cantidad",
            "numero_lote",
            "fecha_vencimiento_lote",
            "dias_para_vencer",
        ]

    def get_dias_para_vencer(self, obj):
        if not obj.fecha_vencimiento_lote:
            return None
        hoy = timezone.now().date()
        return (obj.fecha_vencimiento_lote - hoy).days


class AlertasInventarioListResponseSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField()
    resultados = AlertaInventarioItemSerializer(many=True)


class ResumenAlertasInventarioSerializer(serializers.Serializer):
    cantidad_stocks_bajos = serializers.IntegerField()
    cantidad_stocks_agotados = serializers.IntegerField()
    cantidad_lotes_vencidos = serializers.IntegerField()
    cantidad_lotes_proximo_vencer = serializers.IntegerField()
    total_alertas = serializers.IntegerField()

    stocks_bajos = AlertaInventarioItemSerializer(many=True)
    stocks_agotados = AlertaInventarioItemSerializer(many=True)
    lotes_vencidos = AlertaInventarioItemSerializer(many=True)
    lotes_proximo_vencer = AlertaInventarioItemSerializer(many=True)


class ListadoReposicionSerializer(serializers.Serializer):
    stock_id = serializers.IntegerField()
    producto_id = serializers.IntegerField()
    producto_nombre = serializers.CharField()
    punto_inventario = serializers.CharField()
    cantidad_actual = serializers.DecimalField(max_digits=12, decimal_places=2)
    cantidad_minima = serializers.DecimalField(max_digits=12, decimal_places=2)
    cantidad_faltante = serializers.DecimalField(max_digits=12, decimal_places=2)
    proveedor = serializers.CharField()
