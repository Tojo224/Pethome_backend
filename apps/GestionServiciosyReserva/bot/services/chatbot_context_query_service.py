from ..utils.text_matcher import TextMatcher


class ChatbotContextQueryService:
    @staticmethod
    def detectar_consulta_apoyo(mensaje):
        texto = TextMatcher.normalize(mensaje)

        if not texto:
            return None

        if ChatbotContextQueryService._es_consulta_mascotas(texto):
            return "MASCOTAS"

        if ChatbotContextQueryService._es_consulta_precios(texto):
            return "PRECIOS"

        if ChatbotContextQueryService._es_consulta_servicios(texto):
            return "SERVICIOS"

        if ChatbotContextQueryService._es_consulta_modalidades(texto):
            return "MODALIDADES"

        return None

    @staticmethod
    def _es_consulta_servicios(texto):
        claves = [
            "que servicios",
            "muestrame los servicios",
            "servicios disponibles",
            "servicios hay",
            "listar servicios",
        ]
        return any(clave in texto for clave in claves)

    @staticmethod
    def _es_consulta_mascotas(texto):
        claves = [
            "que mascotas tengo",
            "mis mascotas",
            "mascotas registradas",
            "mascotas tengo",
        ]
        return any(clave in texto for clave in claves)

    @staticmethod
    def _es_consulta_precios(texto):
        claves = [
            "cuanto cuesta",
            "precio de",
            "cuanto sale",
            "precio",
            "coste",
            "costo",
        ]
        return any(clave in texto for clave in claves)

    @staticmethod
    def _es_consulta_modalidades(texto):
        claves = [
            "que modalidades",
            "modalidades hay",
            "a domicilio",
            "en clinica",
            "atienden en clinica",
            "atencion en clinica",
            "modalidad",
        ]
        return any(clave in texto for clave in claves)

