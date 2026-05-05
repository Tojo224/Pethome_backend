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

    REPROGRAMAR = "REPROGRAMAR", "Reprogramar"
    CANCELAR = "CANCELAR", "Cancelar"
    CONFIRMAR = "CONFIRMAR", "Confirmar"

    COMPRAR = "COMPRAR", "Comprar"
    AJUSTAR_STOCK = "AJUSTAR_STOCK", "Ajustar Stock"

    # Grupos y Permisos (RBAC)
    GRUPO_CREADO = "GRUPO_CREADO", "Grupo creado"
    GRUPO_EDITADO = "GRUPO_EDITADO", "Grupo editado"
    GRUPO_ELIMINADO = "GRUPO_ELIMINADO", "Grupo eliminado"
    PERMISO_ASIGNADO = "PERMISO_ASIGNADO", "Permiso asignado"
    PERMISO_EDITADO = "PERMISO_EDITADO", "Permiso editado"
    PERMISO_REMOVIDO = "PERMISO_REMOVIDO", "Permiso removido"

    # Clientes y Mascotas
    CLIENTE_CREADO = "CLIENTE_CREADO", "Cliente creado"
    CLIENTE_EDITADO = "CLIENTE_EDITADO", "Cliente editado"
    CLIENTE_CONSULTADO = "CLIENTE_CONSULTADO", "Cliente consultado"
    CLIENTE_DESACTIVADO = "CLIENTE_DESACTIVADO", "Cliente desactivado"
    MASCOTA_CREADA = "MASCOTA_CREADA", "Mascota creada"
    MASCOTA_EDITADA = "MASCOTA_EDITADA", "Mascota editada"
    MASCOTA_CONSULTADA = "MASCOTA_CONSULTADA", "Mascota consultada"
    MASCOTA_DESACTIVADA = "MASCOTA_DESACTIVADA", "Mascota desactivada"
    PERFIL_MASCOTA_CONSULTADO = "PERFIL_MASCOTA_CONSULTADO", "Perfil de mascota consultado"
    HISTORIAL_SERVICIOS_CONSULTADO = "HISTORIAL_SERVICIOS_CONSULTADO", "Historial de servicios consultado"

    # Servicios y Catálogos
    SERVICIO_CREADO = "SERVICIO_CREADO", "Servicio creado"
    SERVICIO_EDITADO = "SERVICIO_EDITADO", "Servicio editado"
    SERVICIO_CONSULTADO = "SERVICIO_CONSULTADO", "Servicio consultado"
    SERVICIO_ACTIVADO = "SERVICIO_ACTIVADO", "Servicio activado"
    SERVICIO_DESACTIVADO = "SERVICIO_DESACTIVADO", "Servicio desactivado"
    CATEGORIA_SERVICIO_CREADA = "CATEGORIA_SERVICIO_CREADA", "Categoría de servicio creada"
    CATEGORIA_SERVICIO_EDITADA = "CATEGORIA_SERVICIO_EDITADA", "Categoría de servicio editada"
    CATEGORIA_SERVICIO_CONSULTADA = "CATEGORIA_SERVICIO_CONSULTADA", "Categoría de servicio consultada"
    PRECIO_SERVICIO_CREADO = "PRECIO_SERVICIO_CREADO", "Precio de servicio creado"
    PRECIO_SERVICIO_EDITADO = "PRECIO_SERVICIO_EDITADO", "Precio de servicio editado"
    PRECIO_SERVICIO_CONSULTADO = "PRECIO_SERVICIO_CONSULTADO", "Precio de servicio consultado"

    # Citas y Reservas
    CITA_SOLICITADA = "CITA_SOLICITADA", "Cita solicitada"
    CITA_CONSULTADA = "CITA_CONSULTADA", "Cita consultada"
    RESERVA_CONSULTADA = "RESERVA_CONSULTADA", "Reserva consultada"
    RESERVA_MODIFICADA = "RESERVA_MODIFICADA", "Reserva modificada"
    RESERVA_ACTIVADA = "RESERVA_ACTIVADA", "Reserva activada"
    RESERVA_CANCELADA = "RESERVA_CANCELADA", "Reserva cancelada"
    RESERVA_MODIFICACION_FALLIDA = "RESERVA_MODIFICACION_FALLIDA", "Modificación de reserva fallida"
    CITA_SOLICITUD_FALLIDA = "CITA_SOLICITUD_FALLIDA", "Solicitud de cita fallida"

    # Clínica
    CONSULTA_CLINICA_CREADA = "CONSULTA_CLINICA_CREADA", "Consulta clínica creada"
    CONSULTA_CLINICA_CONSULTADA = "CONSULTA_CLINICA_CONSULTADA", "Consulta clínica consultada"
    HISTORIAL_CLINICO_CONSULTADO = "HISTORIAL_CLINICO_CONSULTADO", "Historial clínico consultado"

    # Agenda y Disponibilidad (CU-13)
    AGENDA_CONSULTADA = "AGENDA_CONSULTADA", "Agenda consultada"
    DISPONIBILIDAD_CONSULTADA = "DISPONIBILIDAD_CONSULTADA", "Disponibilidad consultada"
    HORARIO_DISPONIBLE_SELECCIONADO = "HORARIO_DISPONIBLE_SELECCIONADO", "Horario seleccionado"
    CONFLICTO_HORARIO_DETECTADO = "CONFLICTO_HORARIO_DETECTADO", "Conflicto de horario detectado"
    CITA_AGENDADA_DESDE_AGENDA = "CITA_AGENDADA_DESDE_AGENDA", "Cita agendada desde agenda"
    CITA_CONFIRMADA_DESDE_AGENDA = "CITA_CONFIRMADA_DESDE_AGENDA", "Cita confirmada desde agenda"


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
    CLIENTES = "clientes", "Clientes"
    MASCOTAS = "mascotas", "Mascotas"
    CATALOGOS = "catalogos", "Catálogos"
    SERVICIOS = "servicios", "Servicios"
    PRECIOS = "precios", "Precios"
    CITAS = "citas", "Citas"
    CLINICA = "clinica", "Clínica"
    INVENTARIO = "inventario", "Inventario"
    PROVEEDORES = "proveedores", "Proveedores"
    AGENDA_DISPONIBILIDAD = "agenda_disponibilidad", "Agenda y Disponibilidad"
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
    BitacoraAccion.REPROGRAMAR: "{actor} reprogramó {entidad} #{entidad_id} para {nueva_fecha}.",
    BitacoraAccion.CANCELAR: "{actor} canceló {entidad} #{entidad_id}.",
    BitacoraAccion.CONFIRMAR: "{actor} confirmó {entidad} #{entidad_id}.",
    BitacoraAccion.COMPRAR: "{actor} registró compra de {entidad}.",
    BitacoraAccion.AJUSTAR_STOCK: "{actor} ajustó stock de {entidad} #{entidad_id}.",

    # Grupos y Permisos
    BitacoraAccion.GRUPO_CREADO: "{actor} creó el grupo de seguridad '{nombre}'.",
    BitacoraAccion.PERMISO_ASIGNADO: "{actor} asignó un nuevo permiso al grupo #{entidad_id}.",
    
    # Clientes y Mascotas
    BitacoraAccion.CLIENTE_CREADO: "{actor} registró un nuevo cliente: {nombre}.",
    BitacoraAccion.CLIENTE_DESACTIVADO: "{actor} desactivó al cliente {entidad}.",
    BitacoraAccion.MASCOTA_CREADA: "{actor} registró a la mascota {nombre}.",
    BitacoraAccion.MASCOTA_EDITADA: "{actor} actualizó los datos de la mascota {nombre}.",
    BitacoraAccion.MASCOTA_DESACTIVADA: "{actor} eliminó/desactivó a la mascota {nombre}.",
    BitacoraAccion.PERFIL_MASCOTA_CONSULTADO: "{actor} consultó el perfil completo de {nombre}.",
    BitacoraAccion.HISTORIAL_SERVICIOS_CONSULTADO: "{actor} consultó el historial de servicios de {nombre}.",

    # Servicios
    BitacoraAccion.SERVICIO_CREADO: "{actor} creó el servicio: {nombre}.",
    BitacoraAccion.CATEGORIA_SERVICIO_CREADA: "{actor} creó la categoría de servicio: {nombre}.",
    BitacoraAccion.PRECIO_SERVICIO_CREADO: "{actor} asignó un nuevo precio al servicio #{entidad_id}.",

    # Citas
    BitacoraAccion.CITA_SOLICITADA: "Se ha solicitado una nueva cita para {entidad}.",
    BitacoraAccion.RESERVA_CANCELADA: "Se canceló la reserva #{entidad_id}.",

    # Clínica
    BitacoraAccion.CONSULTA_CLINICA_CREADA: "Se registró una nueva consulta clínica para {entidad}.",
    
    # Agenda y Disponibilidad
    BitacoraAccion.AGENDA_CONSULTADA: "{actor} consultó la agenda de la veterinaria para el día {fecha}.",
    BitacoraAccion.DISPONIBILIDAD_CONSULTADA: "{actor} consultó disponibilidad de horarios para {fecha}.",
    BitacoraAccion.CONFLICTO_HORARIO_DETECTADO: "Se detectó un conflicto de horario al intentar agendar en {fecha} {hora}.",
    BitacoraAccion.CITA_AGENDADA_DESDE_AGENDA: "{actor} agendó una nueva cita #{entidad_id} desde el módulo de agenda.",
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