from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.AutenticacionySeguridad.mixins.tenant_mixins import TenantViewMixin
from apps.AutenticacionySeguridad.permissions.tenant_rbac import HasComponentPermission

from .serializers import ChatbotCitasRequestSerializer
from .services.chatbot_orchestrator_service import ChatbotOrchestratorService


class ChatbotCitasView(TenantViewMixin, APIView):
    permission_classes = [IsAuthenticated, HasComponentPermission]
    rbac_component = "SERV_CITAS"

    @extend_schema(
        tags=["Bot Citas"],
        request=ChatbotCitasRequestSerializer,
        responses={
            200: OpenApiResponse(description="Respuesta del chatbot de citas."),
            400: OpenApiResponse(description="Datos invAlidos."),
        },
    )
    
    def post(self, request):
        serializer = ChatbotCitasRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mensaje = serializer.validated_data["mensaje"]
        contexto = serializer.validated_data.get("contexto", {})

        resultado = ChatbotOrchestratorService.procesar_mensaje(
            user=request.user,
            veterinaria_id=self.get_tenant_id(),
            mensaje=mensaje,
            contexto=contexto,
        )

        return Response(resultado, status=status.HTTP_200_OK)