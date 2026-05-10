from django.apps import apps

from ..utils.text_matcher import TextMatcher


class ChatbotMascotaSelector:
    @staticmethod
    def _get_mascota_model():
        """
        Busca dinAmicamente el modelo Mascota para evitar depender del import exacto.
        """
        for model in apps.get_models():
            if model.__name__.lower() == "mascota":
                return model

        raise LookupError("No se encontrA el modelo Mascota en las apps instaladas.")

    @staticmethod
    def listar_mascotas_usuario(*, user, veterinaria_id=None):
        Mascota = ChatbotMascotaSelector._get_mascota_model()

        qs = Mascota.objects.all()

        field_names = {field.name for field in Mascota._meta.fields}

        if "usuario" in field_names:
            qs = qs.filter(usuario_id=user.id_usuario)

        if "veterinaria" in field_names and veterinaria_id:
            qs = qs.filter(veterinaria_id=veterinaria_id)

        if "estado" in field_names:
            qs = qs.filter(estado=True)

        return list(qs)

    @staticmethod
    def buscar_por_nombre(*, user, veterinaria_id=None, nombre):
        mascotas = ChatbotMascotaSelector.listar_mascotas_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
        )

        matches = TextMatcher.find_best_matches(
            nombre,
            mascotas,
            label_getter=lambda mascota: getattr(mascota, "nombre", ""),
            min_score=0.45,
        )

        return matches

    @staticmethod
    def to_option(mascota):
        return {
            "id_mascota": getattr(mascota, "id_mascota", None),
            "nombre": getattr(mascota, "nombre", ""),
        }
    
    @staticmethod
    def obtener_mascota_usuario_por_id(*, user, veterinaria_id=None, id_mascota=None):
        mascotas = ChatbotMascotaSelector.listar_mascotas_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
        )

        for mascota in mascotas:
            if getattr(mascota, "id_mascota", None) == id_mascota:
                return mascota

        return None