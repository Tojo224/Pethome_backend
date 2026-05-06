from django.db import models

class BitacoraAccion(models.TextChoices):
    # Autenticación y Sistema
    LOGIN_EXITOSO = "LOGIN_EXITOSO", "Inicio de sesión exitoso"
    LOGIN_FALLIDO = "LOGIN_FALLIDO", "Inicio de sesión fallido"
    LOGOUT_EXITOSO = "LOGOUT_EXITOSO", "Cierre de sesión exitoso"
    ACCESO_DENEGADO = "ACCESO_DENEGADO", "Acceso denegado"
    INTENTO_ACCESO_OTRO_TENANT = "INTENTO_ACCESO_OTRO_TENANT", "Intento de acceso a otro tenant"
    COMPONENTES_CARGADOS = "COMPONENTES_CARGADOS", "Componentes cargados"

    # Usuarios
    USUARIO_CREADO = "USUARIO_CREADO", "Usuario creado"
    USUARIO_EDITADO = "USUARIO_EDITADO", "Usuario editado"
    USUARIO_ACTIVADO = "USUARIO_ACTIVADO", "Usuario activado"
    USUARIO_DESACTIVADO = "USUARIO_DESACTIVADO", "Usuario desactivado"
    USUARIO_CONSULTADO = "USUARIO_CONSULTADO", "Usuario consultado"
    CAMBIO_PASSWORD = "CAMBIO_PASSWORD", "Cambio de contraseña"

    # Grupos y Permisos
    GRUPO_CREADO = "GRUPO_CREADO", "Grupo creado"
    GRUPO_EDITADO = "GRUPO_EDITADO", "Grupo editado"
    GRUPO_DESACTIVADO = "GRUPO_DESACTIVADO", "Grupo desactivado"
    USUARIO_ASIGNADO_GRUPO = "USUARIO_ASIGNADO_GRUPO", "Usuario asignado a grupo"
    USUARIO_REMOVIDO_GRUPO = "USUARIO_REMOVIDO_GRUPO", "Usuario removido de grupo"
    PERMISO_CREADO = "PERMISO_CREADO", "Permiso creado"
    PERMISO_EDITADO = "PERMISO_EDITADO", "Permiso editado"
    PERMISO_ELIMINADO = "PERMISO_ELIMINADO", "Permiso eliminado"

    # Bitácora
    BITACORA_CONSULTADA = "BITACORA_CONSULTADA", "Bitácora consultada"
    BITACORA_EXPORTADA = "BITACORA_EXPORTADA", "Bitácora exportada"

    # Clientes y Mascotas
    CLIENTE_CREADO = "CLIENTE_CREADO", "Cliente creado"
    CLIENTE_EDITADO = "CLIENTE_EDITADO", "Cliente editado"
    CLIENTE_CONSULTADO = "CLIENTE_CONSULTADO", "Cliente consultado"
    CLIENTE_DESACTIVADO = "CLIENTE_DESACTIVADO", "Cliente desactivado"
    MASCOTA_CREADA = "MASCOTA_CREADA", "Mascota creada"
    MASCOTA_EDITADA = "MASCOTA_EDITADA", "Mascota editada"
    MASCOTA_CONSULTADA = "MASCOTA_CONSULTADA", "Mascota consultada"
    MASCOTA_DESACTIVADA = "MASCOTA_DESACTIVADA", "Mascota desactivada"

    # Servicios y Catálogos
    SERVICIO_CREADO = "SERVICIO_CREADO", "Servicio creado"
    SERVICIO_EDITADO = "SERVICIO_EDITADO", "Servicio editado"
    SERVICIO_ACTIVADO = "SERVICIO_ACTIVADO", "Servicio activado"
    SERVICIO_DESACTIVADO = "SERVICIO_DESACTIVADO", "Servicio desactivado"
    SERVICIO_CONSULTADO = "SERVICIO_CONSULTADO", "Servicio consultado"
    CATEGORIA_SERVICIO_CREADA = "CATEGORIA_SERVICIO_CREADA", "Categoría de servicio creada"
    CATEGORIA_SERVICIO_EDITADA = "CATEGORIA_SERVICIO_EDITADA", "Categoría de servicio editada"
    PRECIO_SERVICIO_CREADO = "PRECIO_SERVICIO_CREADO", "Precio de servicio creado"
    PRECIO_SERVICIO_EDITADO = "PRECIO_SERVICIO_EDITADO", "Precio de servicio editado"
    PRECIO_SERVICIO_CONSULTADO = "PRECIO_SERVICIO_CONSULTADO", "Precio de servicio consultado"

    # Citas, Clínica y Agenda
    CITA_SOLICITADA = "CITA_SOLICITADA", "Cita solicitada"
    CITA_AGENDADA_DESDE_AGENDA = "CITA_AGENDADA_DESDE_AGENDA", "Cita agendada desde agenda"
    CITA_CONFIRMADA_DESDE_AGENDA = "CITA_CONFIRMADA_DESDE_AGENDA", "Cita confirmada desde agenda"
    CITA_CONSULTADA = "CITA_CONSULTADA", "Cita consultada"
    CITA_SOLICITUD_FALLIDA = "CITA_SOLICITUD_FALLIDA", "Solicitud de cita fallida"
    RESERVA_MODIFICADA = "RESERVA_MODIFICADA", "Reserva modificada"
    RESERVA_CANCELADA = "RESERVA_CANCELADA", "Reserva cancelada"
    RESERVA_ACTIVADA = "RESERVA_ACTIVADA", "Reserva activada"
    RESERVA_CONSULTADA = "RESERVA_CONSULTADA", "Reserva consultada"
    RESERVA_MODIFICACION_FALLIDA = "RESERVA_MODIFICACION_FALLIDA", "Modificación de reserva fallida"
    
    CONSULTA_CLINICA_CREADA = "CONSULTA_CLINICA_CREADA", "Consulta clínica creada"
    CONSULTA_CLINICA_CONSULTADA = "CONSULTA_CLINICA_CONSULTADA", "Consulta clínica consultada"
    HISTORIAL_CLINICO_CREADO = "HISTORIAL_CLINICO_CREADO", "Historial clínico creado"
    HISTORIAL_CLINICO_CONSULTADO = "HISTORIAL_CLINICO_CONSULTADO", "Historial clínico consultado"
    RECETA_CREADA = "RECETA_CREADA", "Receta creada"
    TRATAMIENTO_CREADO = "TRATAMIENTO_CREADO", "Tratamiento creado"
    PERFIL_MASCOTA_CONSULTADO = "PERFIL_MASCOTA_CONSULTADO", "Perfil de mascota consultado"
    HISTORIAL_SERVICIOS_CONSULTADO = "HISTORIAL_SERVICIOS_CONSULTADO", "Historial de servicios consultado"
    AGENDA_CONSULTADA = "AGENDA_CONSULTADA", "Agenda consultada"
    DISPONIBILIDAD_CONSULTADA = "DISPONIBILIDAD_CONSULTADA", "Disponibilidad consultada"
    CONFLICTO_HORARIO_DETECTADO = "CONFLICTO_HORARIO_DETECTADO", "Conflicto de horario detectado"
    CATALOGO_CONSULTADO = "CATALOGO_CONSULTADO", "Catálogo consultado"

    # Acciones Genéricas (Legacy)
    CREAR = "CREAR", "Crear"
    ACTUALIZAR = "ACTUALIZAR", "Actualizar"
    ELIMINAR = "ELIMINAR", "Eliminar"
    VISUALIZAR = "VISUALIZAR", "Visualizar"
    EXPORTAR = "EXPORTAR", "Exportar"
    ACTIVAR = "ACTIVAR", "Activar"
    DESACTIVAR = "DESACTIVAR", "Desactivar"


class BitacoraResultado(models.TextChoices):
    EXITO = "EXITO", "Éxito"
    FALLO = "FALLO", "Fallo"


class BitacoraModulo(models.TextChoices):
    AUTENTICACION = "AUTENTICACION", "Autenticación"
    GESTION_USUARIOS = "GESTION_USUARIOS", "Gestión de Usuarios"
    BITACORA = "BITACORA", "Bitácora"
    ROLES_PERMISOS = "ROLES_PERMISOS", "Roles y Permisos"
    CLIENTES = "CLIENTES", "Clientes"
    MASCOTAS = "MASCOTAS", "Mascotas"
    CLINICA = "CLINICA", "Clínica"
    AGENDA_DISPONIBILIDAD = "AGENDA_DISPONIBILIDAD", "Agenda y Disponibilidad"
    CATALOGOS = "CATALOGOS", "Catálogos"
    PRECIOS = "PRECIOS", "Precios"
    SERVICIOS = "SERVICIOS", "Servicios"
    SISTEMA = "SISTEMA", "Sistema"


BITACORA_EVENTOS_DESCRIPCION = {
    BitacoraAccion.LOGIN_EXITOSO: "Inicio de sesión exitoso.",
    BitacoraAccion.LOGIN_FALLIDO: "Intento de inicio de sesión fallido para {correo}.",
    BitacoraAccion.LOGOUT_EXITOSO: "Cierre de sesión exitoso.",
    BitacoraAccion.ACCESO_DENEGADO: "Acceso denegado a {actor} en {entidad}.",
    BitacoraAccion.INTENTO_ACCESO_OTRO_TENANT: "CRÍTICO: Intento de acceso a datos de otra veterinaria por parte de {actor}.",
    BitacoraAccion.COMPONENTES_CARGADOS: "{actor} cargó su catálogo de componentes dinámicos para {plataforma}.",

    BitacoraAccion.USUARIO_CREADO: "{actor} creó un nuevo usuario: {nombre}.",
    BitacoraAccion.USUARIO_EDITADO: "{actor} editó al usuario #{entidad_id}.",
    BitacoraAccion.USUARIO_ACTIVADO: "{actor} activó la cuenta del usuario #{entidad_id}.",
    BitacoraAccion.USUARIO_DESACTIVADO: "{actor} desactivó la cuenta del usuario #{entidad_id}.",
    BitacoraAccion.USUARIO_CONSULTADO: "{actor} consultó información del usuario #{entidad_id}.",
    
    BitacoraAccion.GRUPO_CREADO: "{actor} creó el grupo de seguridad '{nombre}'.",
    BitacoraAccion.GRUPO_EDITADO: "{actor} editó el grupo de seguridad #{entidad_id}.",
    BitacoraAccion.GRUPO_DESACTIVADO: "{actor} desactivó el grupo de seguridad #{entidad_id}.",
    BitacoraAccion.USUARIO_ASIGNADO_GRUPO: "{actor} asignó al usuario #{user_id} al grupo #{entidad_id}.",
    BitacoraAccion.USUARIO_REMOVIDO_GRUPO: "{actor} removió al usuario #{user_id} del grupo #{entidad_id}.",
    
    BitacoraAccion.PERMISO_CREADO: "{actor} creó un nuevo permiso para el grupo #{entidad_id}.",
    BitacoraAccion.PERMISO_EDITADO: "{actor} editó permisos del grupo #{entidad_id}.",
    BitacoraAccion.PERMISO_ELIMINADO: "{actor} eliminó un permiso del grupo #{entidad_id}.",

    BitacoraAccion.BITACORA_CONSULTADA: "{actor} consultó el historial de la bitácora.",
    BitacoraAccion.BITACORA_EXPORTADA: "{actor} exportó los registros de la bitácora.",

    BitacoraAccion.CLIENTE_CREADO: "{actor} registró un nuevo cliente: {nombre}.",
    BitacoraAccion.CLIENTE_EDITADO: "{actor} actualizó datos del cliente #{entidad_id}.",
    BitacoraAccion.CLIENTE_CONSULTADO: "{actor} consultó información del cliente #{entidad_id}.",
    BitacoraAccion.MASCOTA_CREADA: "{actor} registró a la mascota {nombre}.",
    BitacoraAccion.MASCOTA_EDITADA: "{actor} actualizó datos de la mascota {nombre}.",
    BitacoraAccion.MASCOTA_DESACTIVADA: "{actor} eliminó/desactivó a la mascota #{entidad_id}.",
    
    BitacoraAccion.SERVICIO_CREADO: "{actor} creó el servicio '{nombre}'.",
    BitacoraAccion.SERVICIO_EDITADO: "{actor} actualizó el servicio #{entidad_id}.",
    BitacoraAccion.CATEGORIA_SERVICIO_CREADA: "{actor} creó la categoría '{nombre}'.",
    BitacoraAccion.CATEGORIA_SERVICIO_EDITADA: "{actor} actualizó la categoría #{entidad_id}.",
    BitacoraAccion.PRECIO_SERVICIO_CREADO: "{actor} asignó un nuevo precio al servicio #{servicio_id}.",
    BitacoraAccion.PRECIO_SERVICIO_EDITADO: "{actor} actualizó el precio #{entidad_id}.",

    BitacoraAccion.CITA_AGENDADA_DESDE_AGENDA: "Nueva cita #{entidad_id} agendada correctamente.",
    BitacoraAccion.CITA_CONFIRMADA_DESDE_AGENDA: "Cita #{entidad_id} confirmada desde la agenda.",
    BitacoraAccion.RESERVA_MODIFICADA: "Reserva #{entidad_id} modificada.",
    BitacoraAccion.RESERVA_CANCELADA: "Reserva #{entidad_id} cancelada.",
    
    BitacoraAccion.CONSULTA_CLINICA_CREADA: "Se registró una nueva consulta clínica para {entidad}.",
    BitacoraAccion.CONSULTA_CLINICA_CONSULTADA: "Consulta clínica #{entidad_id} visualizada.",
    BitacoraAccion.HISTORIAL_CLINICO_CREADO: "Se aperturó el historial clínico para la mascota {nombre}.",
    BitacoraAccion.HISTORIAL_CLINICO_CONSULTADO: "{actor} consultó el historial clínico de {entidad}.",
    BitacoraAccion.PERFIL_MASCOTA_CONSULTADO: "{actor} consultó el perfil completo de la mascota #{entidad_id}.",
    
    BitacoraAccion.AGENDA_CONSULTADA: "{actor} consultó la agenda para el día {fecha}.",
    BitacoraAccion.DISPONIBILIDAD_CONSULTADA: "{actor} consultó disponibilidad para {fecha}.",
    BitacoraAccion.CATALOGO_CONSULTADO: "{actor} consultó el catálogo de {entidad_tipo}.",
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