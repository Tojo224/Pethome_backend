from django.apps import AppConfig


class NotificacionesySeguimientoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.NotificacionesySeguimiento"

    def ready(self):
        import apps.NotificacionesySeguimiento.signals
        from .firebase_config import initialize_firebase
        initialize_firebase()
