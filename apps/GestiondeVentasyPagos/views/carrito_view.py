from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.GestiondeVentasyPagos.permissions import IsClientForMobileCart
from apps.GestiondeVentasyPagos.serializers import (
    ActualizarItemCarritoSerializer,
    AgregarItemCarritoSerializer,
    CarritoReadSerializer,
)
from apps.GestiondeVentasyPagos.services import CarritoService


class CarritoDetalleView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, IsClientForMobileCart]

    def get(self, request):
        carrito = CarritoService.obtener_carrito(user=request.user, tenant_id=self.get_tenant_id())
        return Response(CarritoReadSerializer(carrito).data)


class CarritoItemCreateView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, IsClientForMobileCart]

    def post(self, request):
        serializer = AgregarItemCarritoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        carrito = CarritoService.agregar_item(
            user=request.user,
            tenant_id=self.get_tenant_id(),
            data=serializer.validated_data,
        )
        return Response(CarritoReadSerializer(carrito).data, status=status.HTTP_201_CREATED)


class CarritoItemDetailView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, IsClientForMobileCart]

    def patch(self, request, detalle_id: int):
        serializer = ActualizarItemCarritoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        carrito = CarritoService.actualizar_cantidad(
            user=request.user,
            tenant_id=self.get_tenant_id(),
            detalle_id=detalle_id,
            cantidad=serializer.validated_data["cantidad"],
        )
        return Response(CarritoReadSerializer(carrito).data)

    def delete(self, request, detalle_id: int):
        carrito = CarritoService.eliminar_item(
            user=request.user,
            tenant_id=self.get_tenant_id(),
            detalle_id=detalle_id,
        )
        return Response(CarritoReadSerializer(carrito).data)


class CarritoVaciarView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, IsClientForMobileCart]

    def delete(self, request):
        CarritoService.vaciar_carrito(user=request.user, tenant_id=self.get_tenant_id())
        return Response(status=status.HTTP_204_NO_CONTENT)
