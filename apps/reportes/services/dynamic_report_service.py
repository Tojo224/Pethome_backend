from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework.exceptions import ValidationError


DECIMAL_OUTPUT = DecimalField(max_digits=14, decimal_places=2)


def _decimal_zero():
    return Value(Decimal("0"), output_field=DECIMAL_OUTPUT)


def _count_metric(field):
    return Count(field)


def _filtered_count_metric(field, **filters):
    return Count(field, filter=Q(**filters))


def _decimal_sum(field):
    return Coalesce(Sum(field), _decimal_zero())


def _inventory_value_metric():
    unit_value = Coalesce(F("precio_venta"), _decimal_zero())
    line_total = ExpressionWrapper(
        F("stocks_por_punto__cantidad") * unit_value,
        output_field=DECIMAL_OUTPUT,
    )
    return Coalesce(Sum(line_total), _decimal_zero())


def _normalize_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _normalize_row(row):
    return {key: _normalize_value(value) for key, value in row.items()}


def _model_field_names(model):
    fields = set()
    for field in model._meta.get_fields():
        name = getattr(field, "name", None)
        attname = getattr(field, "attname", None)
        if name:
            fields.add(name)
        if attname:
            fields.add(attname)
    return fields


def _safe_dimension_alias(dim, dim_cfg, model, source):
    alias = dim_cfg.get("alias")
    if not alias:
        alias = source.replace("__", "_") if "__" in source else dim

    existing_fields = _model_field_names(model)
    if alias not in existing_fields:
        return alias

    base = alias
    suffix = 1
    while alias in existing_fields:
        alias = f"{base}_{suffix}"
        suffix += 1
    return alias


def _build_dimension_annotations(dimensiones, cfg, model):
    annotations = {}
    group_by = []
    display_names = {}

    for dim in dimensiones or []:
        dim_cfg = cfg["allowed_dimensions"].get(dim)
        if not dim_cfg:
            raise ValidationError(f"Dimension no permitida: {dim}")

        source = dim_cfg["source"]
        alias = _safe_dimension_alias(dim, dim_cfg, model, source)
        display_name = dim_cfg.get("alias", dim)

        needs_annotation = dim_cfg.get("kind") == "date" or alias != source or "__" in source
        if needs_annotation:
            if dim_cfg.get("kind") == "date":
                annotations[alias] = TruncDate(source)
            else:
                annotations[alias] = F(source)
            group_by.append(alias)
        else:
            group_by.append(source)

        display_names[group_by[-1]] = display_name

    return annotations, group_by, display_names

def _apply_date_filters(qs, filtros, cfg):
    date_field = cfg.get("date_field")
    if not date_field or not filtros:
        return qs

    is_datetime = cfg.get("date_field_is_datetime", False)
    if filtros.get("fecha_inicio"):
        lookup = f"{date_field}__date__gte" if is_datetime else f"{date_field}__gte"
        qs = qs.filter(**{lookup: filtros.get("fecha_inicio")})
    if filtros.get("fecha_fin"):
        lookup = f"{date_field}__date__lte" if is_datetime else f"{date_field}__lte"
        qs = qs.filter(**{lookup: filtros.get("fecha_fin")})
    return qs


def _build_user_entity_config():
    return {
        "model": "AutenticacionySeguridad.User",
        "date_field": "date_joined",
        "date_field_is_datetime": True,
        "allowed_metrics": {
            "cantidad": lambda: _count_metric("id_usuario"),
            "activos": lambda: _filtered_count_metric("id_usuario", is_active=True),
            "inactivos": lambda: _filtered_count_metric("id_usuario", is_active=False),
            "nuevos": lambda: _filtered_count_metric(
                "id_usuario",
                date_joined__date__gte=timezone.now().date() - timedelta(days=30),
            ),
        },
        "allowed_dimensions": {
            "rol": {"source": "role__nombre"},
            "estado": {"source": "is_active"},
            "fecha": {"source": "date_joined", "kind": "date", "alias": "fecha"},
            "veterinaria": {"source": "veterinaria__nombre"},
        },
    }


ENTITY_MAP = {
    "citas": {
        "model": "GestionServiciosyReserva.Cita",
        "date_field": "fecha_programada",
        "date_field_is_datetime": False,
        "allowed_metrics": {
            "cantidad": lambda: _count_metric("id_cita"),
            "pendientes": lambda: _filtered_count_metric("id_cita", estado="PENDIENTE"),
            "confirmadas": lambda: _filtered_count_metric("id_cita", estado="CONFIRMADA"),
            "canceladas": lambda: _filtered_count_metric("id_cita", estado="CANCELADA"),
            "completadas": lambda: _filtered_count_metric("id_cita", estado="COMPLETADA"),
        },
        "allowed_dimensions": {
            "estado": {"source": "estado"},
            "fecha": {"source": "fecha_programada", "alias": "fecha"},
            "cliente": {"source": "usuario__correo"},
            "mascota": {"source": "mascota__nombre"},
            "veterinaria": {"source": "veterinaria__nombre"},
        },
    },
    "ventas": {
        "model": "GestiondeVentasyPagos.Venta",
        "date_field": "fecha_venta",
        "date_field_is_datetime": True,
        "allowed_metrics": {
            "cantidad": lambda: _count_metric("id_venta"),
            "suma_total": lambda: _decimal_sum("total"),
        },
        "allowed_dimensions": {
            "fecha": {"source": "fecha_venta", "kind": "date", "alias": "fecha"},
            "estado": {"source": "estado_venta", "alias": "estado"},
            "cliente": {"source": "cliente__correo"},
            "mascota": {"source": "mascota__nombre"},
            "veterinaria": {"source": "veterinaria__nombre"},
        },
    },
    "servicios": {
        "model": "GestionServiciosyReserva.Servicio",
        "allowed_metrics": {
            "cantidad": lambda: _count_metric("id_servicio"),
            "activos": lambda: _filtered_count_metric("id_servicio", estado=True),
            "inactivos": lambda: _filtered_count_metric("id_servicio", estado=False),
            "domicilio": lambda: _filtered_count_metric("id_servicio", disponible_domicilio=True),
        },
        "allowed_dimensions": {
            "estado": {"source": "estado"},
            "categoria": {"source": "categoria__nombre"},
            "nombre": {"source": "nombre"},
            "veterinaria": {"source": "veterinaria__nombre"},
        },
    },
    "mascotas": {
        "model": "GestionClientesyMascotas.Mascota",
        "date_field": "fecha_registro",
        "date_field_is_datetime": True,
        "allowed_metrics": {
            "cantidad": lambda: _count_metric("id_mascota"),
            "activas": lambda: _filtered_count_metric("id_mascota", estado=True),
            "inactivas": lambda: _filtered_count_metric("id_mascota", estado=False),
        },
        "allowed_dimensions": {
            "especie": {"source": "especie__nombre"},
            "raza": {"source": "raza__nombre"},
            "sexo": {"source": "sexo"},
            "estado": {"source": "estado"},
            "fecha": {"source": "fecha_registro", "kind": "date", "alias": "fecha"},
            "veterinaria": {"source": "veterinaria__nombre"},
        },
    },
    "productos": {
        "model": "GestionInventarioProveedores.Producto",
        "allowed_metrics": {
            "cantidad": lambda: _count_metric("id_producto"),
            "activos": lambda: _filtered_count_metric("id_producto", estado=True),
            "inactivos": lambda: _filtered_count_metric("id_producto", estado=False),
            "stock_total": lambda: _decimal_sum("stocks_por_punto__cantidad"),
            "valor_inventario": lambda: _inventory_value_metric(),
        },
        "allowed_dimensions": {
            "categoria": {"source": "categoria_producto__nombre"},
            "proveedor": {"source": "proveedor__nombre"},
            "estado": {"source": "estado"},
            "tipo_mascota": {"source": "tipo_mascota"},
            "veterinaria": {"source": "veterinaria__nombre"},
        },
    },
}

USER_ENTITY_CONFIG = _build_user_entity_config()
ENTITY_MAP["clientes"] = USER_ENTITY_CONFIG
ENTITY_MAP["usuarios"] = USER_ENTITY_CONFIG


def generate_dynamic(entity, metricas, dimensiones, filtros, scope, user):
    cfg = ENTITY_MAP.get(entity)
    if not cfg:
        raise ValidationError("Entidad no permitida")

    Model = apps.get_model(cfg["model"]) if isinstance(cfg["model"], str) else cfg["model"]
    qs = Model.objects.all()

    vet = scope.get("veterinaria")
    if vet and hasattr(Model, "_meta") and any(f.name == "veterinaria" for f in Model._meta.fields):
        qs = qs.filter(veterinaria=vet)

    if filtros:
        qs = _apply_date_filters(qs, filtros, cfg)
        if filtros.get("id_veterinaria") and scope.get("global"):
            qs = qs.filter(veterinaria_id=filtros.get("id_veterinaria"))

    annotations = {}
    for metric in metricas or []:
        metric_def = cfg["allowed_metrics"].get(metric)
        if not metric_def:
            raise ValidationError(f"Metrica no permitida: {metric}")
        annotations[metric] = metric_def()

    dimension_annotations, group_by, display_names = _build_dimension_annotations(dimensiones, cfg, Model)
    annotations.update(dimension_annotations)

    if group_by:
        qs = (
            qs.annotate(**dimension_annotations)
            .values(*group_by)
            .annotate(**{k: v for k, v in annotations.items() if k not in group_by})
            .order_by()
        )
        cols = [display_names.get(col, col) for col in group_by] + [
            metric for metric in annotations.keys() if metric not in group_by
        ]
        datos = []
        for row in qs:
            normalized = _normalize_row(dict(row))
            datos.append({display_names.get(key, key): value for key, value in normalized.items()})
    else:
        agg = qs.aggregate(**annotations)
        cols = list(annotations.keys())
        datos = [_normalize_row(agg)]

    return {"titulo": f"Reporte dinamico: {entity}", "columnas": cols, "datos": datos}
