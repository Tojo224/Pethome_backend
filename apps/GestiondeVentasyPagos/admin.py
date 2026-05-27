from django.contrib import admin

from apps.GestiondeVentasyPagos.models import DetalleVenta, Venta


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id_venta", "veterinaria", "usuario_responsable", "estado_venta", "total", "fecha_venta")
    list_filter = ("estado_venta", "veterinaria")
    search_fields = ("id_venta", "usuario_responsable__correo", "cliente__correo")


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ("id_detalle_venta", "venta", "tipo_item", "cantidad", "precio_unitario", "subtotal")
    list_filter = ("tipo_item", "estado")
