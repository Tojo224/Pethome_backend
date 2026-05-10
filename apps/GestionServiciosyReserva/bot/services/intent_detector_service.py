import json
import re

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ..utils.prompt import ChatbotPromptBuilder
from .openrouter_service import OpenRouterService


class IntentDetectorService:
    @staticmethod
    def _inferir_modalidad_desde_texto(mensaje_usuario):
        texto = (mensaje_usuario or "").strip().lower()

        if any(
            fragmento in texto
            for fragmento in [
                "domicilio",
                "a domicilio",
                "en mi casa",
                "mi casa",
            ]
        ):
            return "DOMICILIO"

        if any(
            fragmento in texto
            for fragmento in [
                "clinica",
                "clínica",
                "en clinica",
                "en clínica",
                "veterinaria",
                "en la veterinaria",
            ]
        ):
            return "CLINICA"

        return None

    @staticmethod
    def _limpiar_json_respuesta(texto):
        """
        Limpia respuestas tipo ```json ... ``` por si el modelo devuelve markdown.
        También intenta extraer el primer objeto JSON si viene texto adicional.
        """
        if not texto:
            return texto

        texto = texto.strip()

        if texto.startswith("```"):
            texto = re.sub(r"^```json\s*", "", texto, flags=re.IGNORECASE)
            texto = re.sub(r"^```\s*", "", texto)
            texto = re.sub(r"\s*```$", "", texto)

        texto = texto.strip()

        if not texto.startswith("{"):
            inicio = texto.find("{")
            fin = texto.rfind("}")

            if inicio != -1 and fin != -1 and fin > inicio:
                texto = texto[inicio : fin + 1]

        return texto.strip()

    @staticmethod
    def _validar_estructura(data):
        """
        Validación mínima para asegurar que la IA devolvió la estructura esperada.
        """
        if not isinstance(data, dict):
            raise ValidationError({
                "detail": "La respuesta de la IA no es un objeto JSON válido."
            })

        if "intencion" not in data:
            raise ValidationError({
                "detail": "La respuesta de la IA no contiene el campo intencion.",
                "response": data,
            })

        if "datos" not in data or not isinstance(data["datos"], dict):
            raise ValidationError({
                "detail": "La respuesta de la IA no contiene el objeto datos.",
                "response": data,
            })

        if "faltan" not in data:
            data["faltan"] = []

        if "respuesta" not in data:
            data["respuesta"] = "Verificaremos la información antes de continuar."

        return data

    @staticmethod
    def detectar_intencion(mensaje_usuario):
        fecha_actual = timezone.localdate().isoformat()

        system_prompt = ChatbotPromptBuilder.build_intent_detection_prompt(
            fecha_actual=fecha_actual
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": mensaje_usuario,
            },
        ]

        raw_response = OpenRouterService.chat(messages)
        clean_response = IntentDetectorService._limpiar_json_respuesta(raw_response)

        try:
            data = json.loads(clean_response)
        except json.JSONDecodeError:
            raise ValidationError({
                "detail": "La IA no devolvió JSON válido.",
                "raw_response": raw_response,
            })

        data = IntentDetectorService._validar_estructura(data)
        datos = data.get("datos", {}) or {}

        if not datos.get("modalidad"):
            modalidad = IntentDetectorService._inferir_modalidad_desde_texto(
                mensaje_usuario
            )
            if modalidad:
                datos["modalidad"] = modalidad
                data["datos"] = datos
                data["faltan"] = [
                    campo for campo in (data.get("faltan") or []) if campo != "modalidad"
                ]

        return data
