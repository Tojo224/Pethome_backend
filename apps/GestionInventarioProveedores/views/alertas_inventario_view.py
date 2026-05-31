from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.AutenticacionySeguridad.permissions.permissions import IsAdminOrVeterinarian

from ..selectors.inventario_selector import StockPuntoSelector
from ..serializers.alertas_inventario_serializer import (
    AlertaInventarioItemSerializer,
    AlertasInventarioListResponseSerializer,
    ListadoReposicionSerializer,
)
from ..services.inventario_validacion_service import InventarioValidacionService


class AlertasInventarioViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrVeterinarian]

    def get_veterinaria_id(self, request):
        return request.user.veterinaria_id

    @extend_schema(tags=["Inventario"], responses={200: AlertasInventarioListResponseSerializer})
    @action(detail=False, methods=["get"])
    def stocks_bajos(self, request):
        veterinaria_id = self.get_veterinaria_id(request)
        stocks = StockPuntoSelector.get_stocks_bajos(veterinaria_id)
        serializer = AlertaInventarioItemSerializer(stocks, many=True)
        return Response({"cantidad": stocks.count(), "resultados": serializer.data})

    @extend_schema(tags=["Inventario"], responses={200: AlertasInventarioListResponseSerializer})
    @action(detail=False, methods=["get"])
    def stocks_agotados(self, request):
        veterinaria_id = self.get_veterinaria_id(request)
        stocks = StockPuntoSelector.get_stocks_agotados(veterinaria_id)
        serializer = AlertaInventarioItemSerializer(stocks, many=True)
        return Response({"cantidad": stocks.count(), "resultados": serializer.data})

    @extend_schema(tags=["Inventario"], responses={200: AlertasInventarioListResponseSerializer})
    @action(detail=False, methods=["get"])
    def lotes_vencidos(self, request):
        veterinaria_id = self.get_veterinaria_id(request)
        lotes = StockPuntoSelector.get_lotes_vencidos(veterinaria_id)
        serializer = AlertaInventarioItemSerializer(lotes, many=True)
        return Response({"cantidad": lotes.count(), "resultados": serializer.data})

    @extend_schema(tags=["Inventario"], responses={200: AlertasInventarioListResponseSerializer})
    @action(detail=False, methods=["get"])
    def lotes_proximo_vencer(self, request):
        veterinaria_id = self.get_veterinaria_id(request)
        dias = int(request.query_params.get("dias", 30))
        lotes = StockPuntoSelector.get_lotes_proximo_vencer(veterinaria_id, dias)
        serializer = AlertaInventarioItemSerializer(lotes, many=True)
        return Response({"cantidad": lotes.count(), "resultados": serializer.data})

    @action(detail=False, methods=["get"])
    def resumen_alertas(self, request):
        veterinaria_id = self.get_veterinaria_id(request)
        dias_alerta = int(request.query_params.get("dias", 30))
        alertas_dict = StockPuntoSelector.get_alertas_inventario(veterinaria_id, dias_alerta)
        return Response(
            {
                "cantidad_stocks_bajos": alertas_dict["stocks_bajos"].count(),
                "cantidad_stocks_agotados": alertas_dict["stocks_agotados"].count(),
                "cantidad_lotes_vencidos": alertas_dict["lotes_vencidos"].count(),
                "cantidad_lotes_proximo_vencer": alertas_dict["lotes_proximo_vencer"].count(),
                "total_alertas": (
                    alertas_dict["stocks_bajos"].count()
                    + alertas_dict["stocks_agotados"].count()
                    + alertas_dict["lotes_vencidos"].count()
                    + alertas_dict["lotes_proximo_vencer"].count()
                ),
                "stocks_bajos": AlertaInventarioItemSerializer(alertas_dict["stocks_bajos"], many=True).data,
                "stocks_agotados": AlertaInventarioItemSerializer(alertas_dict["stocks_agotados"], many=True).data,
                "lotes_vencidos": AlertaInventarioItemSerializer(alertas_dict["lotes_vencidos"], many=True).data,
                "lotes_proximo_vencer": AlertaInventarioItemSerializer(
                    alertas_dict["lotes_proximo_vencer"], many=True
                ).data,
            }
        )

    @action(detail=False, methods=["get"])
    def productos_para_reposicion(self, request):
        veterinaria_id = self.get_veterinaria_id(request)
        productos = InventarioValidacionService.obtener_productos_para_reposicion(veterinaria_id)
        productos_ordenados = sorted(productos, key=lambda x: x["cantidad_faltante"], reverse=True)
        serializer = ListadoReposicionSerializer(productos_ordenados, many=True)
        return Response({"cantidad": len(productos_ordenados), "resultados": serializer.data})

    @action(detail=False, methods=["get"])
    def validar_disponibilidad(self, request):
        stock_id = request.query_params.get("stock_id")
        cantidad = float(request.query_params.get("cantidad", 0))

        if not stock_id:
            return Response(
                {"error": "Se requiere proporcionar stock_id y cantidad"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            disponible, mensaje = InventarioValidacionService.validar_producto_disponible(int(stock_id), cantidad)
            return Response(
                {
                    "disponible": disponible,
                    "mensaje": mensaje,
                    "stock_id": stock_id,
                    "cantidad_requerida": cantidad,
                }
            )
        except ValueError:
            return Response({"error": "Parametros invalidos"}, status=status.HTTP_400_BAD_REQUEST)
