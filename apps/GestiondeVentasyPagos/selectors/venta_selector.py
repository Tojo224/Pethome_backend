from django.db.models import Count

from apps.GestiondeVentasyPagos.models import Venta


class VentaSelector:
    @staticmethod
    def get_ventas_by_tenant(veterinaria_id: int):
        return (
            Venta.objects.select_related(
                "veterinaria",
                "usuario_responsable",
                "cliente",
                "mascota",
            )
            .prefetch_related("detalles")
            .filter(veterinaria_id=veterinaria_id)
            .annotate(total_items=Count("detalles"))
            .order_by("-fecha_venta", "-id_venta")
        )

    @staticmethod
    def get_venta_detail(veterinaria_id: int, venta_id: int):
        return (
            Venta.objects.select_related(
                "veterinaria",
                "usuario_responsable",
                "cliente",
                "mascota",
            )
            .prefetch_related(
                "detalles",
                "detalles__producto",
                "detalles__servicio",
                "detalles__precio_servicio",
            )
            .filter(veterinaria_id=veterinaria_id, id_venta=venta_id)
            .first()
        )
