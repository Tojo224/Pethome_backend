from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


UNIDADES_MEDIDA = [
    "Unidad",
    "Caja",
    "Botella",
    "Frasco",
    "Tubo",
    "Blíster",
    "Sobre",
    "Bolsa",
    "Kg",
    "Gramos",
    "Litro",
    "Mililitro",
]


class UnidadMedidaListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"results": UNIDADES_MEDIDA})