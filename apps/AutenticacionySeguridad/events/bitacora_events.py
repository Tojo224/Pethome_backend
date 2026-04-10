from django.db import models


class BitacoraAccion(models.TextChoices):
    LOGIN = "LOGIN", "Inicio de sesión"
    LOGOUT = "LOGOUT", "Cierre de sesión"
    LOGIN_FALLIDO = "LOGIN_FALLIDO", "Inicio de sesión fallido"

    CREAR = "CREAR", "Crear"
    ACTUALIZAR = "ACTUALIZAR", "Actualizar"
    ELIMINAR = "ELIMINAR", "Eliminar"
    VISUALIZAR = "VISUALIZAR", "Visualizar"
    EXPORTAR = "EXPORTAR", "Exportar"

    CAMBIO_PASSWORD = "CAMBIO_PASSWORD", "Cambio de contraseña"
    CAMBIO_PERMISOS = "CAMBIO_PERMISOS", "Cambio de permisos"
    ACCESO_DENEGADO = "ACCESO_DENEGADO", "Acceso denegado"

    ACTIVAR = "ACTIVAR", "Activar"
    DESACTIVAR = "DESACTIVAR", "Desactivar"


class BitacoraResultado(models.TextChoices):
    EXITO = "EXITO", "Éxito"
    FALLO = "FALLO", "Fallo"


class BitacoraModulo(models.TextChoices):
    AUTENTICACION = "autenticacion", "Autenticación"
    USUARIOS = "usuarios", "Usuarios"
    PERFILES = "perfiles", "Perfiles"
    ROLES = "roles", "Roles"
    PERMISOS = "permisos", "Permisos"
    BITACORA = "bitacora", "Bitácora"
    SISTEMA = "sistema", "Sistema"


BITACORA_EVENTOS_DESCRIPCION = {
    BitacoraAccion.LOGIN: "Inicio de sesión exitoso.",
    BitacoraAccion.LOGOUT: "Cierre de sesión exitoso.",
    BitacoraAccion.LOGIN_FALLIDO: "Intento de inicio de sesión fallido para {correo}.",
    BitacoraAccion.CREAR: "{actor} creó {entidad} #{entidad_id}.",
    BitacoraAccion.ACTUALIZAR: "{actor} actualizó {entidad} #{entidad_id}.",
    BitacoraAccion.ELIMINAR: "{actor} eliminó {entidad} #{entidad_id}.",
    BitacoraAccion.VISUALIZAR: "{actor} consultó {entidad} #{entidad_id}.",
    BitacoraAccion.EXPORTAR: "{actor} exportó datos de {entidad}.",
    BitacoraAccion.CAMBIO_PASSWORD: "{actor} cambió la contraseña de {entidad} #{entidad_id}.",
    BitacoraAccion.CAMBIO_PERMISOS: "{actor} modificó permisos de {entidad} #{entidad_id}.",
    BitacoraAccion.ACCESO_DENEGADO: "Acceso denegado a {actor} en {entidad}.",
    BitacoraAccion.ACTIVAR: "{actor} activó {entidad} #{entidad_id}.",
    BitacoraAccion.DESACTIVAR: "{actor} desactivó {entidad} #{entidad_id}.",
}


class _SafeFormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def construir_descripcion_evento(accion: str, **contexto) -> str:
    plantilla = BITACORA_EVENTOS_DESCRIPCION.get(accion, "")
    if not plantilla:
        return ""

    try:
        return plantilla.format_map(_SafeFormatDict(contexto))
    except Exception:
        return plantilla