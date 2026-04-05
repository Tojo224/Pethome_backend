from rest_framework import serializers
from ..models import CategoriaServicio, Servicio



class ServicioSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    class Meta:
        model = Servicio
        fields = ["id_servicio", "nombre", "descripcion", "categoria", "categoria_nombre", "estado"]
    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        queryset = Servicio.objects.filter(nombre__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un servicio con este nombre.")
        return value
    def validate_categoria(self, value):
        if not CategoriaServicio.objects.filter(pk=value.pk, estado=True).exists():
            raise serializers.ValidationError("La categoría seleccionada no es válida o está inactiva.")
        return value 
    
