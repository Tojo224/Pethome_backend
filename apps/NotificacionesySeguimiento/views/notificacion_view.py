from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.NotificacionesySeguimiento.models import Notificacion
from apps.NotificacionesySeguimiento.serializers.notificacion_serializer import NotificacionSerializer

class NotificacionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Vista para que los usuarios consulten su historial de notificaciones.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificacionSerializer

    def get_queryset(self):
        # Aislamiento multi-tenant y por usuario
        return Notificacion.objects.filter(
            usuario=self.request.user,
            veterinaria=self.request.user.veterinaria
        ).order_by("-fecha_creacion")

    @action(detail=True, methods=["post"], url_path="marcar-leida")
    def marcar_leida(self, request, pk=None):
        notificacion = self.get_object()
        notificacion.estado = Notificacion.EstadoNotificacion.LEIDA
        notificacion.fecha_leida = timezone.now()
        notificacion.save()
        return Response({"status": "notificacion marcada como leida"})

    @action(detail=False, methods=["post"], url_path="marcar-todas-leidas")
    def marcar_todas_leidas(self, request):
        self.get_queryset().filter(estado=Notificacion.EstadoNotificacion.ENVIADA).update(
            estado=Notificacion.EstadoNotificacion.LEIDA,
            fecha_leida=timezone.now()
        )
        return Response({"status": "todas las notificaciones marcadas como leidas"})
