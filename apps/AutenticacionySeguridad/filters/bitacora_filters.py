import django_filters

from ..models.bitacora import Bitacora


class BitacoraFilter(django_filters.FilterSet):
    fecha_desde = django_filters.DateTimeFilter(field_name="fecha_hora", lookup_expr="gte")
    fecha_hasta = django_filters.DateTimeFilter(field_name="fecha_hora", lookup_expr="lte")
    id_veterinaria = django_filters.NumberFilter(field_name="veterinaria_id")
    es_global = django_filters.BooleanFilter(method="filter_es_global")

    class Meta:
        model = Bitacora
        fields = [
            "id_veterinaria",
            "es_global",
            "fecha_desde",
            "fecha_hasta",
        ]

    def filter_es_global(self, queryset, name, value):
        if value is True:
            return queryset.filter(veterinaria__isnull=True)
        if value is False:
            return queryset.filter(veterinaria__isnull=False)
        return queryset
