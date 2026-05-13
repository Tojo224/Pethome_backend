import django_filters

from .models import Pedido, Seguimiento

ALLOWED_SEGUIMIENTO_FILTER_PARAMS = {
    "tipo_seguimiento",
    "estado_actual",
    "visible_cliente",
    "pedido_id",
    "cita_id",
    "fecha_desde",
    "fecha_hasta",
}

ALLOWED_PEDIDO_FILTER_PARAMS = {
    "estado_pedido",
    "tipo_entrega",
    "fecha_desde",
    "fecha_hasta",
}


def get_unknown_filter_params(query_params, allowed_params):
    return sorted({key for key in query_params.keys() if key not in allowed_params})


class SeguimientoFilter(django_filters.FilterSet):
    fecha_desde = django_filters.DateFilter(field_name="fecha_hora", lookup_expr="date__gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha_hora", lookup_expr="date__lte")
    pedido_id = django_filters.NumberFilter(field_name="pedido_id")
    cita_id = django_filters.NumberFilter(field_name="cita_id")

    class Meta:
        model = Seguimiento
        fields = [
            "tipo_seguimiento",
            "estado_actual",
            "visible_cliente",
            "pedido_id",
            "cita_id",
            "fecha_desde",
            "fecha_hasta",
        ]

    def is_valid(self):
        is_valid = super().is_valid()
        if not is_valid:
            return False

        fecha_desde = self.form.cleaned_data.get("fecha_desde")
        fecha_hasta = self.form.cleaned_data.get("fecha_hasta")
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            self.form.add_error(
                "fecha_hasta",
                "El rango de fechas es invalido: fecha_desde no puede ser mayor a fecha_hasta.",
            )
            return False
        return True


class PedidoFilter(django_filters.FilterSet):
    fecha_desde = django_filters.DateFilter(field_name="fecha_pedido", lookup_expr="date__gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha_pedido", lookup_expr="date__lte")

    class Meta:
        model = Pedido
        fields = ["estado_pedido", "tipo_entrega", "fecha_desde", "fecha_hasta"]

    def is_valid(self):
        is_valid = super().is_valid()
        if not is_valid:
            return False

        fecha_desde = self.form.cleaned_data.get("fecha_desde")
        fecha_hasta = self.form.cleaned_data.get("fecha_hasta")
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            self.form.add_error(
                "fecha_hasta",
                "El rango de fechas es invalido: fecha_desde no puede ser mayor a fecha_hasta.",
            )
            return False
        return True
