from datetime import date, datetime, timedelta

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.AutenticacionySeguridad.models.user import User
from apps.GestionClientesyMascotas.models.adopcion import Adopcion
from apps.GestionClientesyMascotas.models.mascota import Mascota
from apps.GestionInventarioProveedores.models.producto import Producto
from apps.GestionInventarioProveedores.models.stock_punto import StockPunto
from apps.GestionServiciosyReserva.models.citas import Cita
from apps.GestiondeVentasyPagos.models.detalle_venta import DetalleVenta
from apps.GestiondeVentasyPagos.models.venta import Venta


def _resolve_date_range(periodo=None, fecha_inicio=None, fecha_fin=None):
    today = timezone.now().date()
    if periodo == "hoy":
        return today, today
    if periodo == "semana":
        start = today - timedelta(days=today.weekday())
        return start, today
    if periodo == "mes":
        start = today.replace(day=1)
        return start, today
    if fecha_inicio:
        try:
            start = (
                datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                if isinstance(fecha_inicio, str)
                else fecha_inicio
            )
        except (ValueError, TypeError):
            start = today
        try:
            end = (
                datetime.strptime(fecha_fin, "%Y-%m-%d").date()
                if isinstance(fecha_fin, str)
                else fecha_fin
            ) if fecha_fin else today
        except (ValueError, TypeError):
            end = today
        return start, end
    return None, None


def _filter_by_tenant(qs, scope):
    vet = scope.get("veterinaria")
    if vet:
        return qs.filter(veterinaria=vet)
    return qs


def _calculate_ventas(start, end, scope):
    ventas_qs = _filter_by_tenant(Venta.objects.all(), scope)
    pagadas = ventas_qs.filter(estado_venta="PAGADA")

    if start and end:
        day_filter = Q(fecha_venta__date=start)
        month_filter = Q(
            fecha_venta__date__gte=start,
            fecha_venta__date__lte=end,
        )
        ventas_dia_qs = pagadas.filter(fecha_venta__date=start)
        ventas_periodo_qs = pagadas.filter(
            fecha_venta__date__gte=start,
            fecha_venta__date__lte=end,
        )
    else:
        today = timezone.now().date()
        month_start = today.replace(day=1)
        day_filter = Q(fecha_venta__date=today)
        month_filter = Q(
            fecha_venta__date__gte=month_start,
            fecha_venta__date__lte=today,
        )
        ventas_dia_qs = pagadas.filter(fecha_venta__date=today)
        ventas_periodo_qs = pagadas.filter(
            fecha_venta__date__gte=month_start,
            fecha_venta__date__lte=today,
        )

    ventas_dia = ventas_dia_qs.count()
    ingresos_dia = ventas_dia_qs.aggregate(t=Sum("total"))["t"] or 0
    ventas_mes = ventas_periodo_qs.count()
    ingresos_periodo = ventas_periodo_qs.aggregate(t=Sum("total"))["t"] or 0
    ingresos_totales = pagadas.aggregate(t=Sum("total"))["t"] or 0

    detalles = DetalleVenta.objects.filter(
        venta__in=pagadas,
    )
    if scope.get("veterinaria"):
        detalles = detalles.filter(
            Q(producto__veterinaria=scope["veterinaria"])
            | Q(servicio__veterinaria=scope["veterinaria"]),
        )

    ingresos_productos = (
        detalles.filter(tipo_item=DetalleVenta.TipoItem.PRODUCTO).aggregate(
            t=Sum("subtotal")
        )["t"]
        or 0
    )
    ingresos_servicios = (
        detalles.filter(tipo_item=DetalleVenta.TipoItem.SERVICIO).aggregate(
            t=Sum("subtotal")
        )["t"]
        or 0
    )
    ticket_promedio = (
        pagadas.aggregate(avg=Sum("total") / Count("id_venta"))["avg"] or 0
    )

    productos_mas_vendidos = (
        detalles.filter(
            tipo_item=DetalleVenta.TipoItem.PRODUCTO,
            producto__isnull=False,
        )
        .values("producto__nombre", "producto_id")
        .annotate(total_vendido=Sum("cantidad"))
        .order_by("-total_vendido")[:10]
    )

    ventas_por_dia = (
        ventas_periodo_qs.annotate(
            dia=TruncDate("fecha_venta"),
        )
        .values("dia")
        .annotate(total=Sum("total"), count=Count("id_venta"))
        .order_by("dia")
    )

    return {
        "ventas_dia": ventas_dia,
        "ingresos_dia": float(ingresos_dia),
        "ventas_periodo": ventas_mes,
        "ingresos_periodo": float(ingresos_periodo),
        "ingresos_totales": float(ingresos_totales),
        "ingresos_productos": float(ingresos_productos),
        "ingresos_servicios": float(ingresos_servicios),
        "ticket_promedio": float(ticket_promedio),
        "productos_mas_vendidos": [
            {
                "nombre": p["producto__nombre"],
                "id": p["producto_id"],
                "total_vendido": float(p["total_vendido"]),
            }
            for p in productos_mas_vendidos
        ],
        "ventas_por_dia": [
            {
                "dia": str(v["dia"]),
                "total": float(v["total"]),
                "count": v["count"],
            }
            for v in ventas_por_dia
        ],
    }


def _calculate_reservas(start, end, scope):
    qs = _filter_by_tenant(Cita.objects.all(), scope)

    if start and end:
        qs = qs.filter(fecha_programada__gte=start, fecha_programada__lte=end)

    total = qs.count()
    pendientes = qs.filter(estado=Cita.EstadoChoices.PENDIENTE).count()
    confirmadas = qs.filter(estado=Cita.EstadoChoices.CONFIRMADA).count()
    canceladas = qs.filter(estado=Cita.EstadoChoices.CANCELADA).count()
    completadas = qs.filter(estado=Cita.EstadoChoices.COMPLETADA).count()

    reservas_por_estado = [
        {"estado": "PENDIENTE", "count": pendientes},
        {"estado": "CONFIRMADA", "count": confirmadas},
        {"estado": "CANCELADA", "count": canceladas},
        {"estado": "COMPLETADA", "count": completadas},
    ]

    servicios_mas_solicitados = (
        qs.values(
            "servicio__nombre",
            "servicio_id",
        )
        .annotate(total=Count("id_cita"))
        .order_by("-total")[:10]
    )

    # Próximas reservas (futuras, no canceladas)
    hoy = timezone.now().date()
    proximas = (
        _filter_by_tenant(Cita.objects.all(), scope)
        .filter(
            fecha_programada__gte=hoy,
            estado__in=[
                Cita.EstadoChoices.PENDIENTE,
                Cita.EstadoChoices.CONFIRMADA,
            ],
        )
        .order_by("fecha_programada", "hora_inicio")[:10]
    )

    return {
        "total": total,
        "pendientes": pendientes,
        "confirmadas": confirmadas,
        "canceladas": canceladas,
        "completadas": completadas,
        "por_estado": reservas_por_estado,
        "servicios_mas_solicitados": [
            {
                "nombre": s["servicio__nombre"],
                "id": s["servicio_id"],
                "total": s["total"],
            }
            for s in servicios_mas_solicitados
        ],
        "proximas_reservas": [
            {
                "id": c.id_cita,
                "mascota": c.mascota.nombre if c.mascota else "",
                "servicio": c.servicio.nombre if c.servicio else "",
                "cliente": c.usuario.correo if c.usuario else "",
                "fecha": str(c.fecha_programada),
                "hora": str(c.hora_inicio),
                "estado": c.estado,
            }
            for c in proximas
        ],
    }


def _calculate_clientes_mascotas(start, end, scope):
    clientes_qs = User.objects.filter(is_active=True)
    mascotas_qs = _filter_by_tenant(Mascota.objects.all(), scope)

    vet = scope.get("veterinaria")
    if vet:
        clientes_qs = clientes_qs.filter(veterinaria=vet)

    total_clientes = clientes_qs.count()
    total_mascotas = mascotas_qs.count()

    if start and end:
        clientes_nuevos = clientes_qs.filter(
            date_joined__date__gte=start,
            date_joined__date__lte=end,
        ).count()
        mascotas_nuevas = mascotas_qs.filter(
            fecha_registro__date__gte=start,
            fecha_registro__date__lte=end,
        ).count()
    else:
        today = timezone.now().date()
        month_start = today.replace(day=1)
        clientes_nuevos = clientes_qs.filter(
            date_joined__date__gte=month_start,
        ).count()
        mascotas_nuevas = mascotas_qs.filter(
            fecha_registro__date__gte=month_start,
        ).count()

    return {
        "total_clientes": total_clientes,
        "clientes_nuevos_periodo": clientes_nuevos,
        "total_mascotas": total_mascotas,
        "mascotas_nuevas_periodo": mascotas_nuevas,
    }


def _calculate_inventario(start, end, scope):
    productos_qs = _filter_by_tenant(Producto.objects.all(), scope)

    total_productos = productos_qs.count()

    stock_qs = _filter_by_tenant(StockPunto.objects.all(), scope)

    stock_bajo = stock_qs.filter(cantidad__lte=F("cantidad_minima"))

    hoy = timezone.now().date()
    alerta_dias = 30
    proximos_vencer = stock_qs.filter(
        fecha_vencimiento_lote__isnull=False,
        fecha_vencimiento_lote__gte=hoy,
        fecha_vencimiento_lote__lte=hoy + timedelta(days=alerta_dias),
    )

    vencidos = stock_qs.filter(
        fecha_vencimiento_lote__isnull=False,
        fecha_vencimiento_lote__lt=hoy,
    )

    return {
        "total_productos": total_productos,
        "stock_bajo": [
            {
                "id": s.id_stock,
                "producto_id": s.producto_id,
                "producto": s.producto.nombre if s.producto else "",
                "cantidad": float(s.cantidad),
                "cantidad_minima": float(s.cantidad_minima),
            }
            for s in stock_bajo
        ],
        "proximos_a_vencer": [
            {
                "id": s.id_stock,
                "producto_id": s.producto_id,
                "producto": s.producto.nombre if s.producto else "",
                "lote": s.numero_lote,
                "fecha_vencimiento": str(s.fecha_vencimiento_lote),
            }
            for s in proximos_vencer
        ],
        "vencidos": [
            {
                "id": s.id_stock,
                "producto_id": s.producto_id,
                "producto": s.producto.nombre if s.producto else "",
                "lote": s.numero_lote,
                "fecha_vencimiento": str(s.fecha_vencimiento_lote),
            }
            for s in vencidos
        ],
    }


def _calculate_adopciones(scope):
    qs = _filter_by_tenant(Adopcion.objects.all(), scope)

    disponibles = qs.filter(estado_adopcion=Adopcion.ESTADO_DISPONIBLE).count()
    en_proceso = qs.filter(estado_adopcion=Adopcion.ESTADO_EN_PROCESO).count()
    adoptados = qs.filter(estado_adopcion=Adopcion.ESTADO_ADOPTADO).count()
    inactivos = qs.filter(estado_adopcion=Adopcion.ESTADO_INACTIVO).count()

    hoy = timezone.now().date()
    month_start = hoy.replace(day=1)
    nuevas_publicaciones = qs.filter(
        fecha_publicacion__date__gte=month_start
    ).count()

    # Lista de animales disponibles/en proceso
    lista = qs.filter(
        estado_adopcion__in=[
            Adopcion.ESTADO_DISPONIBLE,
            Adopcion.ESTADO_EN_PROCESO,
        ]
    ).order_by("-fecha_publicacion")[:10]

    return {
        "disponibles": disponibles,
        "en_proceso": en_proceso,
        "adoptados": adoptados,
        "inactivos": inactivos,
        "nuevas_publicaciones_periodo": nuevas_publicaciones,
        "lista": [
            {
                "id": a.id_adopcion,
                "nombre": a.nombre,
                "especie": a.especie.nombre if a.especie else "",
                "estado": a.estado_adopcion,
                "foto": a.foto,
            }
            for a in lista
        ],
    }


def _calculate_alertas(reservas, inventario, adopciones):
    alertas = []

    if reservas["pendientes"] > 0:
        alertas.append(
            {
                "tipo": "reservas_pendientes",
                "mensaje": f"{reservas['pendientes']} reservas pendientes",
                "severidad": "media",
                "cantidad": reservas["pendientes"],
            }
        )

    stock_bajo_count = len(inventario["stock_bajo"])
    if stock_bajo_count > 0:
        alertas.append(
            {
                "tipo": "stock_bajo",
                "mensaje": f"{stock_bajo_count} productos con stock bajo",
                "severidad": "alta",
                "cantidad": stock_bajo_count,
            }
        )

    proximos_vencer_count = len(inventario["proximos_a_vencer"])
    if proximos_vencer_count > 0:
        alertas.append(
            {
                "tipo": "proximos_a_vencer",
                "mensaje": f"{proximos_vencer_count} lotes próximos a vencer",
                "severidad": "media",
                "cantidad": proximos_vencer_count,
            }
        )

    vencidos_count = len(inventario["vencidos"])
    if vencidos_count > 0:
        alertas.append(
            {
                "tipo": "vencidos",
                "mensaje": f"{vencidos_count} lotes vencidos",
                "severidad": "alta",
                "cantidad": vencidos_count,
            }
        )

    if adopciones["en_proceso"] > 0:
        alertas.append(
            {
                "tipo": "adopciones_en_proceso",
                "mensaje": f"{adopciones['en_proceso']} adopciones en proceso",
                "severidad": "baja",
                "cantidad": adopciones["en_proceso"],
            }
        )

    return alertas


def build_dashboard_kpis(scope, periodo=None, fecha_inicio=None, fecha_fin=None):
    start, end = _resolve_date_range(periodo, fecha_inicio, fecha_fin)

    ventas = _calculate_ventas(start, end, scope)
    reservas = _calculate_reservas(start, end, scope)
    clientes_mascotas = _calculate_clientes_mascotas(start, end, scope)
    inventario = _calculate_inventario(start, end, scope)
    adopciones = _calculate_adopciones(scope)
    alertas = _calculate_alertas(reservas, inventario, adopciones)

    return {
        "resumen": {
            "ventas_dia": ventas["ventas_dia"],
            "ingresos_dia": ventas["ingresos_dia"],
            "ventas_periodo": ventas["ventas_periodo"],
            "ingresos_periodo": ventas["ingresos_periodo"],
            "ingresos_totales": ventas["ingresos_totales"],
            "ticket_promedio": ventas["ticket_promedio"],
            "clientes_total": clientes_mascotas["total_clientes"],
            "clientes_nuevos_periodo": clientes_mascotas["clientes_nuevos_periodo"],
            "mascotas_total": clientes_mascotas["total_mascotas"],
            "mascotas_nuevas_periodo": clientes_mascotas["mascotas_nuevas_periodo"],
            "reservas_pendientes": reservas["pendientes"],
            "productos_stock_bajo": len(inventario["stock_bajo"]),
            "adopciones_disponibles": adopciones["disponibles"],
        },
        "ventas": {
            "por_dia": ventas["ventas_por_dia"],
            "productos_mas_vendidos": ventas["productos_mas_vendidos"],
            "ingresos_productos": ventas["ingresos_productos"],
            "ingresos_servicios": ventas["ingresos_servicios"],
        },
        "reservas": {
            "total": reservas["total"],
            "por_estado": reservas["por_estado"],
            "proximas_reservas": reservas["proximas_reservas"],
            "servicios_mas_solicitados": reservas["servicios_mas_solicitados"],
        },
        "servicios": {
            "mas_solicitados": reservas["servicios_mas_solicitados"],
        },
        "inventario": {
            "total_productos": inventario["total_productos"],
            "stock_bajo": inventario["stock_bajo"],
            "proximos_a_vencer": inventario["proximos_a_vencer"],
            "vencidos": inventario["vencidos"],
        },
        "clientes_mascotas": {
            "total_clientes": clientes_mascotas["total_clientes"],
            "clientes_nuevos_periodo": clientes_mascotas["clientes_nuevos_periodo"],
            "total_mascotas": clientes_mascotas["total_mascotas"],
            "mascotas_nuevas_periodo": clientes_mascotas["mascotas_nuevas_periodo"],
        },
        "adopciones": {
            "disponibles": adopciones["disponibles"],
            "en_proceso": adopciones["en_proceso"],
            "adoptados": adopciones["adoptados"],
            "inactivos": adopciones["inactivos"],
            "nuevas_publicaciones_periodo": adopciones["nuevas_publicaciones_periodo"],
            "lista": adopciones["lista"],
        },
        "alertas": alertas,
        "ultima_actualizacion": timezone.now().isoformat(),
    }
