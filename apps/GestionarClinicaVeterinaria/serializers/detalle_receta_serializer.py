from rest_framework import serializers
from apps.GestionarClinicaVeterinaria.models import DetalleReceta


class DetalleRecetaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = DetalleReceta
        fields = [
            "id_detalle_receta",
            "receta",
            "producto",
            "producto_nombre",
            "medicamento",
            "dosis",
            "frecuencia",
            "duracion_dias",
            "indicaciones_adicionales",
        ]
        read_only_fields = ["id_detalle_receta"]