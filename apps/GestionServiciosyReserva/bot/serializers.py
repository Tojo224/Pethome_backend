from rest_framework import serializers


class ChatbotCitasRequestSerializer(serializers.Serializer):
    mensaje = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=1000,
    )

    contexto = serializers.DictField(
        required=False,
        allow_empty=True,
    )