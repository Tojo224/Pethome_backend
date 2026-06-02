from datetime import datetime

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate


def _parse_date(d):
    if not d:
        return None
    try:
        return datetime.fromisoformat(d).date()
    except Exception:
        return None


def citas_por_estado(filtros, scope):
    from apps.GestionServiciosyReserva.models.citas import Cita

    qs = Cita.objects.all()
    vet = scope.get("veterinaria")
    if vet:
        qs = qs.filter(veterinaria=vet)

    fecha_i = _parse_date(filtros.get("fecha_inicio") if filtros else None)
    fecha_f = _parse_date(filtros.get("fecha_fin") if filtros else None)
    if fecha_i:
        qs = qs.filter(fecha_programada__gte=fecha_i)
    if fecha_f:
        qs = qs.filter(fecha_programada__lte=fecha_f)

    if filtros and filtros.get("id_veterinario"):
        qs = qs.filter(usuario_id=filtros.get("id_veterinario"))

    data = qs.values("estado").annotate(cantidad=Count("id_cita")).order_by("-cantidad")
    columnas = ["estado", "cantidad"]
    return {"titulo": "Citas por estado", "columnas": columnas, "datos": list(data)}


def ingresos_por_rango(filtros, scope):
    from apps.GestiondeVentasyPagos.models.venta import Venta

    qs = Venta.objects.filter(estado=True)
    vet = scope.get("veterinaria")
    if vet:
        qs = qs.filter(veterinaria=vet)

    fecha_i = _parse_date(filtros.get("fecha_inicio") if filtros else None)
    fecha_f = _parse_date(filtros.get("fecha_fin") if filtros else None)
    if fecha_i:
        qs = qs.filter(fecha_venta__date__gte=fecha_i)
    if fecha_f:
        qs = qs.filter(fecha_venta__date__lte=fecha_f)

    data = (
        qs.annotate(fecha=TruncDate("fecha_venta"))
        .values("fecha")
        .annotate(total=Sum("total"))
        .order_by("fecha")
    )
    columnas = ["fecha", "total"]
    rows = [{"fecha": r["fecha"].isoformat(), "total": float(r["total"] or 0)} for r in data]
    return {"titulo": "Ingresos por rango", "columnas": columnas, "datos": rows}


def servicios_mas_solicitados(filtros, scope):
    from apps.GestionServiciosyReserva.models.citas import Cita

    qs = Cita.objects.all()
    vet = scope.get("veterinaria")
    if vet:
        qs = qs.filter(veterinaria=vet)

    fecha_i = _parse_date(filtros.get("fecha_inicio") if filtros else None)
    fecha_f = _parse_date(filtros.get("fecha_fin") if filtros else None)
    if fecha_i:
        qs = qs.filter(fecha_programada__gte=fecha_i)
    if fecha_f:
        qs = qs.filter(fecha_programada__lte=fecha_f)

    data = (
        qs.values("servicio__id_servicio", "servicio__nombre")
        .annotate(cantidad=Count("id_cita"))
        .order_by("-cantidad")
    )
    columnas = ["id_servicio", "nombre", "cantidad"]
    rows = [
        {
            "id_servicio": r["servicio__id_servicio"],
            "nombre": r["servicio__nombre"],
            "cantidad": r["cantidad"],
        }
        for r in data
    ]
    return {"titulo": "Servicios mas solicitados", "columnas": columnas, "datos": rows}


def clientes_registrados(filtros, scope):
    from django.apps import apps
    from django.conf import settings

    UserModel = apps.get_model(settings.AUTH_USER_MODEL)

    qs = UserModel.objects.filter(is_active=True)
    vet = scope.get("veterinaria")
    if vet:
        qs = qs.filter(veterinaria=vet)

    fecha_i = _parse_date(filtros.get("fecha_inicio") if filtros else None)
    fecha_f = _parse_date(filtros.get("fecha_fin") if filtros else None)
    if fecha_i:
        qs = qs.filter(date_joined__date__gte=fecha_i)
    if fecha_f:
        qs = qs.filter(date_joined__date__lte=fecha_f)

    data = qs.values("role__nombre").annotate(cantidad=Count("id_usuario")).order_by("-cantidad")
    columnas = ["rol", "cantidad"]
    rows = [{"rol": r["role__nombre"], "cantidad": r["cantidad"]} for r in data]
    return {"titulo": "Usuarios por rol (clientes)", "columnas": columnas, "datos": rows}


def mascotas_registradas(filtros, scope):
    from apps.GestionClientesyMascotas.models.mascota import Mascota

    qs = Mascota.objects.all()
    vet = scope.get("veterinaria")
    if vet:
        qs = qs.filter(veterinaria=vet)

    fecha_i = _parse_date(filtros.get("fecha_inicio") if filtros else None)
    fecha_f = _parse_date(filtros.get("fecha_fin") if filtros else None)
    if fecha_i:
        qs = qs.filter(fecha_registro__date__gte=fecha_i)
    if fecha_f:
        qs = qs.filter(fecha_registro__date__lte=fecha_f)

    data = qs.values("especie__nombre").annotate(cantidad=Count("id_mascota")).order_by("-cantidad")
    columnas = ["especie", "cantidad"]
    rows = [{"especie": r["especie__nombre"], "cantidad": r["cantidad"]} for r in data]
    return {"titulo": "Mascotas registradas", "columnas": columnas, "datos": rows}


def veterinarios_mas_atenciones(filtros, scope):
    from apps.GestionServiciosyReserva.models.citas import Cita

    qs = Cita.objects.all()
    vet = scope.get("veterinaria")
    if vet:
        qs = qs.filter(veterinaria=vet)

    fecha_i = _parse_date(filtros.get("fecha_inicio") if filtros else None)
    fecha_f = _parse_date(filtros.get("fecha_fin") if filtros else None)
    if fecha_i:
        qs = qs.filter(fecha_programada__gte=fecha_i)
    if fecha_f:
        qs = qs.filter(fecha_programada__lte=fecha_f)

    data = (
        qs.values("usuario_id", "usuario__correo")
        .annotate(atenciones=Count("id_cita"))
        .order_by("-atenciones")
    )
    columnas = ["id_veterinario", "correo", "atenciones"]
    rows = [
        {
            "id_veterinario": r["usuario_id"],
            "correo": r["usuario__correo"],
            "atenciones": r["atenciones"],
        }
        for r in data
    ]
    return {"titulo": "Veterinarios con mas atenciones", "columnas": columnas, "datos": rows}


STATIC_REPORTS = {
    "citas_por_estado": citas_por_estado,
    "ingresos_por_rango": ingresos_por_rango,
    "servicios_mas_solicitados": servicios_mas_solicitados,
    "clientes_registrados": clientes_registrados,
    "mascotas_registradas": mascotas_registradas,
    "veterinarios_mas_atenciones": veterinarios_mas_atenciones,
}


def list_static_reports():
    return [
        {"slug": "citas_por_estado", "titulo": "Citas por estado"},
        {"slug": "ingresos_por_rango", "titulo": "Ingresos por rango"},
        {"slug": "servicios_mas_solicitados", "titulo": "Servicios mas solicitados"},
        {"slug": "clientes_registrados", "titulo": "Clientes registrados"},
        {"slug": "mascotas_registradas", "titulo": "Mascotas registradas"},
        {"slug": "veterinarios_mas_atenciones", "titulo": "Veterinarios con mas atenciones"},
    ]


def generate_static(slug, filtros, scope):
    fn = STATIC_REPORTS.get(slug)
    if not fn:
        raise ValueError("Reporte estatico no encontrado")
    return fn(filtros or {}, scope)
