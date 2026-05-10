from ...models.servicios import Servicio
from ..utils.text_matcher import TextMatcher


class ChatbotServicioSelector:
    @staticmethod
    def listar_servicios_activos(*, veterinaria_id):
        return list(
            Servicio.objects.select_related("categoria")
            .filter(
                veterinaria_id=veterinaria_id,
                estado=True,
            )
            .order_by("nombre")
        )

    @staticmethod
    def buscar_por_nombre(*, veterinaria_id, nombre):
        servicios = ChatbotServicioSelector.listar_servicios_activos(
            veterinaria_id=veterinaria_id
        )

        def label_getter(servicio):
            categoria_nombre = ""
            if getattr(servicio, "categoria", None):
                categoria_nombre = getattr(servicio.categoria, "nombre", "")

            return f"{servicio.nombre} {servicio.descripcion or ''} {categoria_nombre}"

        matches = TextMatcher.find_best_matches(
            nombre,
            servicios,
            label_getter=label_getter,
            min_score=0.45,
        )

        return matches

    @staticmethod
    def to_option(servicio):
        categoria_nombre = None

        if getattr(servicio, "categoria", None):
            categoria_nombre = getattr(servicio.categoria, "nombre", None)

        return {
            "id_servicio": servicio.id_servicio,
            "nombre": servicio.nombre,
            "descripcion": servicio.descripcion,
            "categoria_nombre": categoria_nombre,
            "duracion_estimada": servicio.duracion_estimada,
            "disponible_domicilio": servicio.disponible_domicilio,
        }
    
    @staticmethod
    def obtener_servicio_activo_por_id(*, veterinaria_id, id_servicio):
        return Servicio.objects.filter(
            veterinaria_id=veterinaria_id,
            id_servicio=id_servicio,
            estado=True,
        ).first()