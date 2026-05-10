import re

from .chatbot_response_builder import ChatbotResponseBuilder
from ..utils.text_matcher import TextMatcher


class ChatbotSelectionResolverService:
    ORDINALES = {
        "primera": 1,
        "primer": 1,
        "uno": 1,
        "segunda": 2,
        "segundo": 2,
        "dos": 2,
        "tercera": 3,
        "tercer": 3,
        "tres": 3,
        "cuarta": 4,
        "cuarto": 4,
        "cuatro": 4,
        "quinta": 5,
        "quinto": 5,
        "cinco": 5,
    }

    @staticmethod
    def resolver_opcion_por_mensaje(*, mensaje, opciones):
        """
        Resuelve una opción a partir del mensaje escrito por el usuario.

        Permite:
        - "1"
        - "la primera"
        - "uno"
        - "baño y peluquería"
        - "peluquería"
        """

        if not opciones:
            return None

        mensaje_norm = TextMatcher.normalize(mensaje)

        # 1. Si el usuario manda un número directo: "1", "2", "3"
        if mensaje_norm.isdigit():
            numero = int(mensaje_norm)
            for opcion in opciones:
                if opcion.get("numero") == numero:
                    return opcion

        numero_en_frase = re.search(r"\b(\d+)\b", mensaje_norm)
        if numero_en_frase:
            numero = int(numero_en_frase.group(1))
            for opcion in opciones:
                if opcion.get("numero") == numero:
                    return opcion

        # 2. Si el usuario dice "la primera", "segunda", etc.
        for palabra, numero in ChatbotSelectionResolverService.ORDINALES.items():
            if palabra in mensaje_norm:
                for opcion in opciones:
                    if opcion.get("numero") == numero:
                        return opcion

        # 3. Buscar por nombre o texto de la opción
        matches = TextMatcher.find_best_matches(
            mensaje,
            opciones,
            label_getter=lambda opcion: (
                opcion.get("nombre")
                or opcion.get("servicio_nombre")
                or opcion.get("mascota_nombre")
                or opcion.get("texto")
                or ""
            ),
            min_score=0.35,
        )

        if matches:
            return matches[0]["item"]

        return None

    @staticmethod
    def respuesta_no_entendida(*, contexto):
        opciones = contexto.get("opciones", [])

        texto_opciones = []
        for opcion in opciones:
            numero = opcion.get("numero")
            nombre = (
                opcion.get("nombre")
                or opcion.get("servicio_nombre")
                or opcion.get("mascota_nombre")
                or opcion.get("texto")
                or "Opción"
            )
            texto_opciones.append(f"{numero}. {nombre}")

        opciones_texto = "\n".join(texto_opciones)

        return ChatbotResponseBuilder.error(
            code="SELECCION_NO_ENTENDIDA",
            respuesta=(
                "No pude identificar cuál opción elegiste. "
                "Por favor escribe el número o el nombre de una de estas opciones:\n"
                f"{opciones_texto}"
            ),
            contexto=contexto,
            data={
                "opciones": opciones,
            },
        )
