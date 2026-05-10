from rest_framework.exceptions import ValidationError

from ..models.precioservicio import PrecioServicio


class PrecioServicioEspecificoService:
    @staticmethod
    def listar_por_servicio(
        *,
        veterinaria_id,
        servicio_id,
        modalidad=None,
    ):
        """
        Lista precios activos de un servicio específico dentro del tenant actual.
        Si se envía modalidad, filtra por CLINICA o DOMICILIO.
        """

        qs = PrecioServicio.objects.select_related("servicio").filter(
            veterinaria_id=veterinaria_id,
            servicio_id=servicio_id,
            servicio__veterinaria_id=veterinaria_id,
            estado=True,
            servicio__estado=True,
        )

        if modalidad:
            modalidad_normalizada = str(modalidad).strip().upper()
            qs = qs.filter(modalidad__iexact=modalidad_normalizada)

        return qs.order_by("precio", "id_precio")

    @staticmethod
    def obtener_precio_unico(
        *,
        veterinaria_id,
        servicio_id,
        modalidad,
    ):
        """
        Devuelve un único precio activo para un servicio y modalidad.
        Útil para el bot cuando ya sabe servicio + modalidad.
        """

        precios = PrecioServicioEspecificoService.listar_por_servicio(
            veterinaria_id=veterinaria_id,
            servicio_id=servicio_id,
            modalidad=modalidad,
        )

        if not precios.exists():
            raise ValidationError(
                {
                    "detail": "No existe un precio activo para el servicio y modalidad indicados.",
                    "code": "PRECIO_SERVICIO_NO_ENCONTRADO",
                }
            )

        if precios.count() > 1:
            raise ValidationError(
                {
                    "detail": "Existe más de un precio activo para este servicio y modalidad.",
                    "code": "PRECIO_SERVICIO_AMBIGUO",
                }
            )

        return precios.first()