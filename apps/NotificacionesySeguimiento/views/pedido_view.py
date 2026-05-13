from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..filters import (
    ALLOWED_PEDIDO_FILTER_PARAMS,
    PedidoFilter,
    get_unknown_filter_params,
)
from ..permissions import HasVeterinariaWithoutSuperadmin
from ..selectors import PedidoSelector
from ..serializers import PedidoDetailSerializer, PedidoListSerializer


class PedidoListView(APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaWithoutSuperadmin]

    def get(self, request):
        unknown_params = get_unknown_filter_params(request.query_params, ALLOWED_PEDIDO_FILTER_PARAMS)
        if unknown_params:
            return Response(
                {
                    "detail": "Parametros de filtro invalidos.",
                    "errors": {
                        "query_params": [
                            f"Parametros no permitidos: {', '.join(unknown_params)}."
                        ]
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = PedidoSelector.get_pedidos_for_user(request.user)
        filterset = PedidoFilter(request.GET, queryset=queryset)

        if not filterset.is_valid():
            return Response(
                {"detail": "Parametros de filtro invalidos.", "errors": filterset.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PedidoListSerializer(filterset.qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PedidoDetailView(APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaWithoutSuperadmin]

    def get(self, request, id_pedido):
        pedido = PedidoSelector.get_pedido_detail_for_user(request.user, id_pedido)
        if pedido is None:
            return Response(
                {"detail": "Pedido no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PedidoDetailSerializer(pedido, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
