from rest_framework import serializers

from .models import ReporteGenerado


class FormatoReporteField(serializers.ChoiceField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            normalized = data.strip().upper()
            alias_map = {
                "PDF": "PDF",
                "EXCEL": "EXCEL",
                "XLSX": "EXCEL",
                "HTML": "HTML",
            }
            data = alias_map.get(normalized, normalized)
        return super().to_internal_value(data)


class ReporteGeneradoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="id_reporte", read_only=True)

    class Meta:
        model = ReporteGenerado
        fields = "__all__"


class GenerarEstaticoSerializer(serializers.Serializer):
    slug = serializers.CharField(required=False)
    tipo_reporte = serializers.CharField(required=False, write_only=True)
    filtros = serializers.JSONField(required=False)
    fecha_inicio = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    fecha_fin = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    id_veterinaria = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    id_veterinario = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    formato = FormatoReporteField(choices=["PDF", "EXCEL", "HTML"], default="PDF")

    def validate(self, attrs):
        tipo_reporte = attrs.pop("tipo_reporte", None)
        slug = attrs.get("slug") or tipo_reporte
        if not slug:
            raise serializers.ValidationError({"slug": "Este campo es requerido."})

        filtros = dict(attrs.get("filtros") or {})
        for key in ("fecha_inicio", "fecha_fin", "id_veterinaria", "id_veterinario"):
            value = attrs.pop(key, None)
            if value not in (None, ""):
                filtros[key] = value

        attrs["slug"] = slug
        attrs["filtros"] = filtros
        return attrs


class GenerarDinamicoSerializer(serializers.Serializer):
    entidad = serializers.CharField()
    metricas = serializers.ListField(child=serializers.CharField())
    dimensiones = serializers.ListField(child=serializers.CharField(), required=False)
    filtros = serializers.JSONField(required=False)
    formato = FormatoReporteField(choices=["PDF", "EXCEL", "HTML"], default="PDF")
