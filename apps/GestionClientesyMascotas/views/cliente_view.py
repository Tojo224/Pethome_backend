"""Views para Cliente - Endpoints CRUD."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404

from apps.GestionClientesyMascotas.models import Cliente
from apps.GestionClientesyMascotas.api.serializers.cliente_serializer import (
    ClienteSerializer,
    ClienteCreateSerializer,
    ClienteUpdateSerializer,
)
from apps.GestionClientesyMascotas.selectors import cliente_selector
from apps.GestionClientesyMascotas.services import cliente_service


class ClienteListCreateView(APIView):
    """
    GET /api/clientes/ - Obtiene lista de clientes
    POST /api/clientes/ - Crea un nuevo cliente
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtiene lista de todos los clientes con búsqueda opcional."""
        search_term = request.query_params.get('search', '')
        activos_solo = request.query_params.get('activos', 'false').lower() == 'true'
        
        if search_term:
            clientes = cliente_selector.buscar_clientes(
                search_term=search_term,
                activos_solo=activos_solo
            )
        else:
            clientes = cliente_selector.get_all_clientes(activos_solo=activos_solo)
        
        # Paginación
        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginated_datos = paginator.paginate_queryset(clientes, request)
        
        serializer = ClienteSerializer(paginated_datos, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Crea un nuevo cliente."""
        serializer = ClienteCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cliente = cliente_service.crear_cliente(
                usuario=serializer.validated_data['usuario'],
                datos=serializer.validated_data
            )
            return Response(
                ClienteSerializer(cliente).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ClienteDetailView(APIView):
    """
    GET /api/clientes/{id}/ - Obtiene detalles de un cliente
    PUT /api/clientes/{id}/ - Actualiza un cliente
    DELETE /api/clientes/{id}/ - Elimina un cliente
    """
    permission_classes = [IsAuthenticated]
    
    def get_cliente(self, cliente_id):
        """Helper para obtener cliente o retornar 404."""
        cliente = cliente_selector.get_cliente_by_id(cliente_id)
        if not cliente:
            return None
        return cliente
    
    def get(self, request, cliente_id):
        """Obtiene los detalles de un cliente específico."""
        cliente = self.get_cliente(cliente_id)
        if not cliente:
            return Response(
                {"detail": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ClienteSerializer(cliente)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, cliente_id):
        """Actualiza completamente un cliente (PUT)."""
        cliente = self.get_cliente(cliente_id)
        if not cliente:
            return Response(
                {"detail": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ClienteUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cliente_actualizado = cliente_service.actualizar_cliente(
            cliente,
            serializer.validated_data
        )
        
        return Response(
            ClienteSerializer(cliente_actualizado).data,
            status=status.HTTP_200_OK
        )
    
    def patch(self, request, cliente_id):
        """Actualiza parcialmente un cliente (PATCH)."""
        cliente = self.get_cliente(cliente_id)
        if not cliente:
            return Response(
                {"detail": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ClienteUpdateSerializer(
            data=request.data,
            partial=True
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cliente_actualizado = cliente_service.actualizar_cliente(
            cliente,
            serializer.validated_data
        )
        
        return Response(
            ClienteSerializer(cliente_actualizado).data,
            status=status.HTTP_200_OK
        )
    
    def delete(self, request, cliente_id):
        """Elimina un cliente."""
        cliente = self.get_cliente(cliente_id)
        if not cliente:
            return Response(
                {"detail": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        cliente_service.eliminar_cliente(cliente)
        return Response(
            {"detail": "Cliente eliminado exitosamente."},
            status=status.HTTP_204_NO_CONTENT
        )


class ClienteToggleActivoView(APIView):
    """
    POST /api/clientes/{id}/toggle-activo/ - Activa/Desactiva un cliente
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, cliente_id):
        """Alterna el estado activo/inactivo de un cliente."""
        cliente = cliente_selector.get_cliente_by_id(cliente_id)
        if not cliente:
            return Response(
                {"detail": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if cliente.activo:
            cliente = cliente_service.desactivar_cliente(cliente)
        else:
            cliente = cliente_service.activar_cliente(cliente)
        
        return Response(
            {
                "detail": f"Cliente {'desactivado' if not cliente.activo else 'activado'} exitosamente.",
                "cliente": ClienteSerializer(cliente).data
            },
            status=status.HTTP_200_OK
        )


class ClientePorUsuarioView(APIView):
    """
    GET /api/clientes/usuario/{usuario_id}/ - Obtiene el cliente de un usuario
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, usuario_id):
        """Obtiene el cliente asociado a un usuario."""
        cliente = cliente_selector.get_cliente_by_usuario(usuario_id)
        if not cliente:
            return Response(
                {"detail": "Cliente no encontrado para este usuario."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ClienteSerializer(cliente)
        return Response(serializer.data, status=status.HTTP_200_OK)
