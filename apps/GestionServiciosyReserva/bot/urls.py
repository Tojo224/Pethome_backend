from django.urls import path

from .views import ChatbotCitasView


urlpatterns = [
    path("chat/", ChatbotCitasView.as_view(), name="bot-citas-chat"),
]