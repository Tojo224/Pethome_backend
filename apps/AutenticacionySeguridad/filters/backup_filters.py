from django_filters import FilterSet, CharFilter, DateTimeFromToRangeFilter, BooleanFilter
from ..models.backup_restore import BackupRestore


class BackupRestoreFilter(FilterSet):
    tipo = CharFilter(field_name="tipo", lookup_expr="iexact")
    estado = CharFilter(field_name="estado", lookup_expr="iexact")
    fecha_hora = DateTimeFromToRangeFilter(field_name="fecha_hora")
    proveedor_almacenamiento = CharFilter(
        field_name="proveedor_almacenamiento",
        lookup_expr="icontains"
    )

    class Meta:
        model = BackupRestore
        fields = ["tipo", "estado", "fecha_hora", "proveedor_almacenamiento"]
