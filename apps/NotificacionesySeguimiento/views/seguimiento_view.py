from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..filters import (
    ALLOWED_SEGUIMIENTO_FILTER_PARAMS,
    SeguimientoFilter,
    get_unknown_filter_params,
)
from ..permissions import HasVeterinariaWithoutSuperadmin
from ..selectors import SeguimientoSelector
from ..serializers import SeguimientoDetailSerializer, SeguimientoListSerializer


class SeguimientoListView(APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaWithoutSuperadmin]

    def get(self, request):
        unknown_params = get_unknown_filter_params(request.query_params, ALLOWED_SEGUIMIENTO_FILTER_PARAMS)
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

        queryset = SeguimientoSelector.get_seguimientos_for_user(request.user)
        filterset = SeguimientoFilter(request.GET, queryset=queryset)

        if not filterset.is_valid():
            return Response(
                {"detail": "Parametros de filtro invalidos.", "errors": filterset.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SeguimientoListSerializer(filterset.qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SeguimientoDetailView(APIView):
    permission_classes = [IsAuthenticated, HasVeterinariaWithoutSuperadmin]

    def get(self, request, id_seguimiento):
        seguimiento = SeguimientoSelector.get_seguimiento_detail_for_user(request.user, id_seguimiento)
        if seguimiento is None:
            return Response(
                {"detail": "Seguimiento no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SeguimientoDetailSerializer(seguimiento, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
