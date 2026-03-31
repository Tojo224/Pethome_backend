from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from ..models import Perfil
from ..serializers import PerfilSerializer, PerfilCreateSerializer

class PerfilView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    # IMPORTANTE: Definir el queryset base para los filtros
    queryset = Perfil.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # Filtros exactos
    filterset_fields = {
        'usuario__is_active': ['exact'],
        'usuario__role__nombre': ['exact'],
    }
    
    # Barra de búsqueda
    search_fields = ['nombre', 'usuario__correo', 'telefono', 'direccion']

    def get(self, request):
        queryset = self.queryset.all()
        
        # Aplicar filtros manualmente
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(request, queryset, self)

        serializer = PerfilSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PerfilCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                perfil = serializer.save()
                # Para la respuesta, devolvemos el formato de lectura (con correo, rol, etc.)
                response_serializer = PerfilSerializer(perfil)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PerfilClienteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    # Configuramos los mismos backends de filtrado
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # Filtros exactos (Estado ya que el Rol siempre será Cliente)
    filterset_fields = {
        'usuario__is_active': ['exact'],
    }
    
    # Barra de búsqueda (Searchbar)
    search_fields = ['nombre', 'usuario__correo', 'telefono', 'direccion']

    def get_queryset(self):
        # 💡 La magia ocurre aquí: filtramos el queryset base por el nombre del rol
        return Perfil.objects.filter(usuario__role__nombre='Cliente')

    def get(self, request):
        queryset = self.get_queryset()
        
        # Aplicamos los filtros y búsqueda sobre el queryset ya filtrado de clientes
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(request, queryset, self)

        serializer = PerfilSerializer(queryset, many=True)
        return Response(serializer.data)

# --- ESTA ES LA CLASE QUE FALTABA ---
class PerfilDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        perfil = get_object_or_404(Perfil, pk=pk)
        serializer = PerfilSerializer(perfil)
        return Response(serializer.data)

    def put(self, request, pk):
        perfil = get_object_or_404(Perfil, pk=pk)
        serializer = PerfilSerializer(perfil, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        perfil = get_object_or_404(Perfil, pk=pk)
        perfil.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)