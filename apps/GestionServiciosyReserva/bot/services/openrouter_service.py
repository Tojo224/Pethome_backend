import json
import requests

from django.conf import settings
from rest_framework.exceptions import ValidationError


class OpenRouterService:
    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    @staticmethod
    def chat(messages, temperature=0.2):
        api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        model = getattr(settings, "OPENROUTER_MODEL", "")

        if not api_key:
            raise ValidationError({
                "detail": "OPENROUTER_API_KEY no está configurada."
            })

        if not model:
            raise ValidationError({
                "detail": "OPENROUTER_MODEL no está configurado."
            })

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", "http://localhost:8000"),
            "X-OpenRouter-Title": getattr(settings, "OPENROUTER_SITE_NAME", "PetHome Chatbot"),
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        try:
            response = requests.post(
                OpenRouterService.API_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise ValidationError({
                "detail": "No se pudo conectar con OpenRouter.",
                "error": str(exc),
            })

        if response.status_code >= 400:
            raise ValidationError({
                "detail": "OpenRouter devolvió un error.",
                "status_code": response.status_code,
                "response": response.text,
            })

        data = response.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise ValidationError({
                "detail": "Respuesta inesperada de OpenRouter.",
                "response": data,
            })
