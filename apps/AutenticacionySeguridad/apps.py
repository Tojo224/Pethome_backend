from django.apps import AppConfig
from django.db.backends.signals import connection_created


def set_public_search_path(sender, connection, **kwargs):
    if connection.vendor != 'postgresql':
        return

    with connection.cursor() as cursor:
        cursor.execute('SET search_path TO public;')


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.AutenticacionySeguridad'

    def ready(self):
        connection_created.connect(set_public_search_path, dispatch_uid='pethome_set_public_search_path')
