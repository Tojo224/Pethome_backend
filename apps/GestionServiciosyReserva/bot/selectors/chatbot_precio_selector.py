from ...models.precioservicio import PrecioServicio


class ChatbotPrecioSelector:
    @staticmethod
    def listar_por_servicio_y_modalidad(*, veterinaria_id, servicio_id, modalidad):
        modalidad = str(modalidad or "").strip().upper()

        qs = PrecioServicio.objects.select_related("servicio").filter(
            veterinaria_id=veterinaria_id,
            servicio_id=servicio_id,
            estado=True,
            servicio__estado=True,
        )

        if modalidad:
            qs = qs.filter(modalidad__iexact=modalidad)

        return list(qs.order_by("precio", "id_precio"))

    @staticmethod
    def obtener_unico_por_servicio_y_modalidad(*, veterinaria_id, servicio_id, modalidad):
        precios = ChatbotPrecioSelector.listar_por_servicio_y_modalidad(
            veterinaria_id=veterinaria_id,
            servicio_id=servicio_id,
            modalidad=modalidad,
        )

        if len(precios) == 1:
            return precios[0]

        return None

    @staticmethod
    def to_option(precio):
        return {
            "id_precio": precio.id_precio,
            "servicio": precio.servicio_id,
            "servicio_nombre": precio.servicio.nombre if precio.servicio_id else None,
            "variacion": precio.variacion,
            "modalidad": precio.modalidad,
            "precio": str(precio.precio),
            "descripcion": precio.descripcion,
        }
    
    @staticmethod
    def obtener_precio_valido_por_id(
        *,
        veterinaria_id,
        id_precio,
        servicio_id,
        modalidad,
    ):
        modalidad = str(modalidad or "").strip().upper()

        return PrecioServicio.objects.select_related("servicio").filter(
            id_precio=id_precio,
            veterinaria_id=veterinaria_id,
            servicio_id=servicio_id,
            modalidad__iexact=modalidad,
            estado=True,
            servicio__estado=True,
            servicio__veterinaria_id=veterinaria_id,
        ).first()