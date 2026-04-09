"""
EQUIPO AVISO IMPORTANTE ESTO PARA CADA APP
El filters.py se encarga de filtrar los datos que se envian a los endpoints.

Delegamos la lógica de filtrado a django-filter para permitir 
búsquedas dinámicas por URL sin ensuciar el QuerySet principal.

Funcionamiento: 
1. Lee los parámetros de la URL.
2. 'field_name' indica la columna en la BD.
3. 'lookup_expr' define la comparación (gte: >=, lte: <=, icontains: busca texto).

Parámetros de fecha:
- fecha_desde
- fecha_hasta

Formato recomendado para fecha/hora: ISO 8601.
Ejemplos válidos:
- 2026-04-08T12:00:00Z
- 2026-04-08T12:00:00-04:00
- 2026-04-08 12:00:00
"""

import django_filters

from .events.bitacora_events import BitacoraAccion, BitacoraModulo, BitacoraResultado
from .models.bitacora import Bitacora


class BitacoraFilter(django_filters.FilterSet):
    fecha_desde = django_filters.DateTimeFilter(field_name="fecha_hora", lookup_expr="gte")
    fecha_hasta = django_filters.DateTimeFilter(field_name="fecha_hora", lookup_expr="lte")
    usuario_id = django_filters.NumberFilter(field_name="usuario_id")
    accion = django_filters.ChoiceFilter(field_name="accion", choices=BitacoraAccion.choices)
    resultado = django_filters.ChoiceFilter(field_name="resultado", choices=BitacoraResultado.choices)
    modulo = django_filters.ChoiceFilter(field_name="modulo", choices=BitacoraModulo.choices)
    descripcion = django_filters.CharFilter(field_name="descripcion", lookup_expr="icontains")
    entidad_tipo = django_filters.CharFilter(field_name="entidad_tipo", lookup_expr="icontains")
    entidad_id = django_filters.CharFilter(field_name="entidad_id", lookup_expr="exact")
    ip = django_filters.CharFilter(field_name="ip", lookup_expr="exact")

    class Meta:
        model = Bitacora
        fields = [
            "usuario_id",
            "accion",
            "resultado",
            "modulo",
            "descripcion",
            "entidad_tipo",
            "entidad_id",
            "ip",
            "fecha_desde",
            "fecha_hasta",
        ]