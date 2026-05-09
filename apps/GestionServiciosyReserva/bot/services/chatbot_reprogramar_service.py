from datetime import datetime, timedelta

from django.utils import timezone

from .chatbot_response_builder import ChatbotResponseBuilder
from .chatbot_selection_resolver_service import ChatbotSelectionResolverService

from ..selectors.chatbot_cita_selector import ChatbotCitaSelector
from ..utils.text_matcher import TextMatcher
from ..utils.time_utils import ChatbotTimeUtils

from ...models.citas import Cita
from ...selectors.servicios_selector import CitaSelector
from ...services.citas_service import CitaService
from ...serializers.citas_serializer import CitaSerializer


class ChatbotReprogramarService:
    @staticmethod
    def _enumerar_opciones(opciones):
        opciones_enumeradas = []

        for index, opcion in enumerate(opciones, start=1):
            opcion_con_numero = dict(opcion)
            opcion_con_numero["numero"] = index
            opciones_enumeradas.append(opcion_con_numero)

        return opciones_enumeradas

    @staticmethod
    def _formatear_cita(cita):
        mascota_nombre = getattr(getattr(cita, "mascota", None), "nombre", "Mascota")
        servicio_nombre = getattr(getattr(cita, "servicio", None), "nombre", "Servicio")
        fecha = cita.fecha_programada.isoformat() if cita.fecha_programada else ""
        hora = cita.hora_inicio.strftime("%H:%M") if cita.hora_inicio else ""
        return f"{mascota_nombre} - {servicio_nombre} - {fecha} {hora}".strip()

    @staticmethod
    def _armar_respuesta_opciones_citas(opciones):
        lineas = ["Estas son tus citas activas:"]

        for opcion in opciones:
            fecha = opcion.get("fecha_programada") or ""
            hora_inicio = str(opcion.get("hora_inicio") or "")[:5]
            mascota_nombre = opcion.get("mascota_nombre") or "Mascota"
            servicio_nombre = opcion.get("servicio_nombre") or "Servicio"
            lineas.append(
                f"{opcion.get('numero')}. {mascota_nombre} - {servicio_nombre} - {fecha} {hora_inicio}"
            )

        lineas.append("\nEscribe el número de la cita que deseas reprogramar.")
        return "\n".join(lineas)

    @staticmethod
    def _usuario_confirma(mensaje):
        texto = TextMatcher.normalize(mensaje)

        afirmaciones = [
            "si",
            "sí",
            "confirmo",
            "confirmar",
            "dale",
            "ok",
            "okay",
            "correcto",
            "acepto",
            "reprogramar",
            "reprograma",
        ]

        return any(TextMatcher.normalize(palabra) in texto for palabra in afirmaciones)

    @staticmethod
    def _usuario_cancela(mensaje):
        texto = TextMatcher.normalize(mensaje)

        negaciones = [
            "no",
            "mejor no",
            "mantener",
            "no cambiar",
            "cancelar operacion",
            "cancelar operación",
            "detener",
        ]

        return any(TextMatcher.normalize(palabra) in texto for palabra in negaciones)

    @staticmethod
    def _validar_cita_reprogramable(cita):
        if not cita:
            return ChatbotResponseBuilder.error(
                code="CITA_NO_VALIDA",
                respuesta="No pude validar la cita seleccionada.",
            )

        if cita.estado == Cita.EstadoChoices.CANCELADA:
            return ChatbotResponseBuilder.error(
                code="CITA_CANCELADA_NO_REPROGRAMABLE",
                respuesta="No se puede reprogramar una cita cancelada.",
            )

        if cita.estado == Cita.EstadoChoices.COMPLETADA:
            return ChatbotResponseBuilder.error(
                code="CITA_COMPLETADA_NO_REPROGRAMABLE",
                respuesta="No se puede reprogramar una cita completada.",
            )

        if cita.estado not in [
            Cita.EstadoChoices.PENDIENTE,
            Cita.EstadoChoices.CONFIRMADA,
        ]:
            return ChatbotResponseBuilder.error(
                code="CITA_NO_VALIDA",
                respuesta="La cita seleccionada no se puede reprogramar en su estado actual.",
            )

        return None

    @staticmethod
    def _calcular_hora_fin(cita, nueva_fecha, nueva_hora_inicio):
        servicio = getattr(cita, "servicio", None)
        duracion = getattr(servicio, "duracion_estimada", None) if servicio else None

        try:
            duracion = int(duracion)
        except (TypeError, ValueError):
            duracion = None

        if not duracion or duracion <= 0:
            return None

        inicio_dt = datetime.combine(nueva_fecha, nueva_hora_inicio)
        fin_dt = inicio_dt + timedelta(minutes=duracion)
        return fin_dt.time()

    @staticmethod
    def _obtener_horarios_disponibles(*, veterinaria_id, fecha_programada, duracion_minutos, excluir_cita_id, cantidad=6):
        HORA_APERTURA = 8
        HORA_CIERRE = 18
        SLOT_MINUTOS = 30

        inicio_dia = datetime.combine(
            fecha_programada,
            datetime.strptime(f"{HORA_APERTURA}:00", "%H:%M").time(),
        )
        fin_dia = datetime.combine(
            fecha_programada,
            datetime.strptime(f"{HORA_CIERRE}:00", "%H:%M").time(),
        )

        ahora = timezone.localtime()
        horarios = []
        actual = inicio_dia

        while actual < fin_dia:
            fin_slot = actual + timedelta(minutes=duracion_minutos)

            if fin_slot > fin_dia:
                break

            actual_aware = timezone.make_aware(
                actual,
                timezone.get_current_timezone(),
            )

            if actual_aware <= ahora:
                actual += timedelta(minutes=SLOT_MINUTOS)
                continue

            ocupado = CitaSelector.verificar_conflicto_horario(
                veterinaria_id,
                fecha_programada,
                actual.time(),
                fin_slot.time(),
                excluir_cita_id=excluir_cita_id,
            )

            if not ocupado:
                horarios.append(
                    {
                        "numero": len(horarios) + 1,
                        "hora_inicio": actual.time().strftime("%H:%M:%S"),
                        "hora_fin": fin_slot.time().strftime("%H:%M:%S"),
                        "texto": (
                            f"{actual.time().strftime('%H:%M')} - "
                            f"{fin_slot.time().strftime('%H:%M')}"
                        ),
                    }
                )

            if len(horarios) >= cantidad:
                break

            actual += timedelta(minutes=SLOT_MINUTOS)

        return horarios

    @staticmethod
    def _responder_conflicto_con_horarios(*, veterinaria_id, cita, fecha_programada, data):
        servicio = getattr(cita, "servicio", None)
        duracion = getattr(servicio, "duracion_estimada", None) if servicio else None

        try:
            duracion = int(duracion)
        except (TypeError, ValueError):
            duracion = None

        if not duracion or duracion <= 0:
            return ChatbotResponseBuilder.error(
                code="DURACION_SERVICIO_INVALIDA",
                respuesta=(
                    "La cita seleccionada no tiene una duración válida configurada. "
                    "No puedo sugerir horarios automáticamente."
                ),
                data={"id_cita": getattr(cita, "id_cita", None)},
            )

        horarios = ChatbotReprogramarService._obtener_horarios_disponibles(
            veterinaria_id=veterinaria_id,
            fecha_programada=fecha_programada,
            duracion_minutos=duracion,
            excluir_cita_id=getattr(cita, "id_cita", None),
        )

        if not horarios:
            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_REPROGRAMACION",
                respuesta=(
                    "Ese horario ya está ocupado y no encontré otros horarios disponibles "
                    "para esa fecha. Indícame otra fecha u hora."
                ),
                faltan=["fecha_programada", "hora_inicio"],
                data={
                    "id_cita": getattr(cita, "id_cita", None),
                },
            )

        lineas = [
            "Ese horario ya está ocupado. Estos horarios están disponibles:",
        ]

        for horario in horarios:
            lineas.append(f"{horario['numero']}. {horario['texto']}")

        lineas.append("\nEscribe el número o la hora que deseas.")

        return ChatbotResponseBuilder.needs_selection(
            tipo="HORARIO",
            estado="ESPERANDO_SELECCION_HORARIO_REPROGRAMACION",
            respuesta="\n".join(lineas),
            opciones=horarios,
            data=data,
        )

    @staticmethod
    def _resolver_reprogramacion(*, user, veterinaria_id, id_cita, fecha_programada, hora_inicio):
        cita = ChatbotCitaSelector.obtener_cita_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
            id_cita=id_cita,
        )

        error_cita = ChatbotReprogramarService._validar_cita_reprogramable(cita)
        if error_cita:
            return error_cita

        nueva_fecha = ChatbotTimeUtils.to_date(fecha_programada)
        nueva_hora_inicio = ChatbotTimeUtils.to_time(hora_inicio)

        if not nueva_fecha or not nueva_hora_inicio:
            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_REPROGRAMACION",
                respuesta="¿Para qué nueva fecha y hora deseas reprogramar la cita?",
                faltan=["fecha_programada", "hora_inicio"],
                data={"id_cita": cita.id_cita},
            )

        ahora = timezone.localtime()
        fecha_hora_nueva = timezone.make_aware(
            datetime.combine(nueva_fecha, nueva_hora_inicio),
            timezone.get_current_timezone(),
        )

        if fecha_hora_nueva <= ahora:
            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_REPROGRAMACION",
                respuesta="No puedo reprogramar una cita en una fecha u hora pasada. Indícame una fecha y hora futuras.",
                faltan=["fecha_programada", "hora_inicio"],
                data={"id_cita": cita.id_cita},
            )

        hora_fin = ChatbotReprogramarService._calcular_hora_fin(
            cita,
            nueva_fecha,
            nueva_hora_inicio,
        )

        if not hora_fin:
            return ChatbotResponseBuilder.error(
                code="DURACION_SERVICIO_INVALIDA",
                respuesta=(
                    "La cita seleccionada no tiene una duración válida configurada. "
                    "No puedo reprogramarla automáticamente."
                ),
                data={"id_cita": cita.id_cita},
            )

        hora_apertura = datetime.strptime("08:00", "%H:%M").time()
        hora_cierre = datetime.strptime("18:00", "%H:%M").time()

        if nueva_hora_inicio < hora_apertura or hora_fin > hora_cierre:
            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_REPROGRAMACION",
                respuesta="El horario debe estar dentro de la atención de 08:00 a 18:00. Indícame otra hora.",
                faltan=["hora_inicio"],
                data={"id_cita": cita.id_cita, "fecha_programada": nueva_fecha.isoformat()},
            )

        ocupado = CitaSelector.verificar_conflicto_horario(
            veterinaria_id,
            nueva_fecha,
            nueva_hora_inicio,
            hora_fin,
            excluir_cita_id=cita.id_cita,
        )

        if ocupado:
            return ChatbotReprogramarService._responder_conflicto_con_horarios(
                veterinaria_id=veterinaria_id,
                cita=cita,
                fecha_programada=nueva_fecha,
                data={
                    "id_cita": cita.id_cita,
                    "fecha_programada": nueva_fecha.isoformat(),
                },
            )

        mascota_nombre = getattr(getattr(cita, "mascota", None), "nombre", "Mascota")
        servicio_nombre = getattr(getattr(cita, "servicio", None), "nombre", "Servicio")
        fecha_actual = cita.fecha_programada.isoformat() if cita.fecha_programada else ""
        hora_actual = cita.hora_inicio.strftime("%H:%M") if cita.hora_inicio else ""

        return ChatbotResponseBuilder.needs_confirmation(
            estado="ESPERANDO_CONFIRMACION_REPROGRAMAR_CITA",
            respuesta=(
                f"¿Confirmas que deseas reprogramar la cita de {mascota_nombre} para {servicio_nombre}?\n"
                f"Fecha actual: {fecha_actual} {hora_actual}\n"
                f"Nueva fecha: {nueva_fecha.isoformat()} {nueva_hora_inicio.strftime('%H:%M')}\n\n"
                "Responde sí para reprogramar o no para mantener la cita actual."
            ),
            data={
                "id_cita": cita.id_cita,
                "fecha_programada": nueva_fecha.isoformat(),
                "hora_inicio": nueva_hora_inicio.strftime("%H:%M:%S"),
                "hora_fin": hora_fin.strftime("%H:%M:%S"),
            },
        )

    @staticmethod
    def iniciar_reprogramacion(*, user, veterinaria_id, interpretacion):
        datos = interpretacion.get("datos", {}) or {}
        fecha_programada = datos.get("fecha_programada")
        hora_inicio = datos.get("hora_inicio")

        citas_activas = list(
            ChatbotCitaSelector.listar_citas_activas_usuario(
                user=user,
                veterinaria_id=veterinaria_id,
            )
        )

        if not citas_activas:
            return ChatbotResponseBuilder.success(
                accion="SIN_CITAS_ACTIVAS",
                respuesta="No encontré citas activas para reprogramar.",
                data={"citas": []},
                contexto=None,
            )

        if len(citas_activas) == 1:
            cita = citas_activas[0]

            if fecha_programada and hora_inicio:
                return ChatbotReprogramarService._resolver_reprogramacion(
                    user=user,
                    veterinaria_id=veterinaria_id,
                    id_cita=cita.id_cita,
                    fecha_programada=fecha_programada,
                    hora_inicio=hora_inicio,
                )

            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_REPROGRAMACION",
                respuesta=(
                    "Encontré esta cita activa:\n"
                    f"{ChatbotReprogramarService._formatear_cita(cita)}.\n\n"
                    "¿Para qué nueva fecha y hora deseas reprogramarla?"
                ),
                faltan=["fecha_programada", "hora_inicio"],
                data={
                    "id_cita": cita.id_cita,
                },
            )

        opciones = ChatbotReprogramarService._enumerar_opciones(
            [
                ChatbotCitaSelector.to_option(cita)
                for cita in citas_activas
            ]
        )

        return ChatbotResponseBuilder.needs_selection(
            tipo="CITA",
            estado="ESPERANDO_SELECCION_CITA_REPROGRAMAR",
            respuesta=ChatbotReprogramarService._armar_respuesta_opciones_citas(opciones),
            opciones=opciones,
            data={
                "fecha_programada": fecha_programada,
                "hora_inicio": hora_inicio,
            },
        )

    @staticmethod
    def continuar_seleccion_cita_reprogramar(*, user, veterinaria_id, mensaje, contexto):
        opcion = ChatbotSelectionResolverService.resolver_opcion_por_mensaje(
            mensaje=mensaje,
            opciones=contexto.get("opciones", []),
        )

        if not opcion:
            return ChatbotSelectionResolverService.respuesta_no_entendida(
                contexto=contexto
            )

        id_cita = opcion.get("id_cita")
        cita = ChatbotCitaSelector.obtener_cita_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
            id_cita=id_cita,
        )

        error_cita = ChatbotReprogramarService._validar_cita_reprogramable(cita)
        if error_cita:
            return error_cita

        data_ctx = contexto.get("data", {}) or {}
        fecha_programada = data_ctx.get("fecha_programada")
        hora_inicio = data_ctx.get("hora_inicio")

        if fecha_programada and hora_inicio:
            return ChatbotReprogramarService._resolver_reprogramacion(
                user=user,
                veterinaria_id=veterinaria_id,
                id_cita=cita.id_cita,
                fecha_programada=fecha_programada,
                hora_inicio=hora_inicio,
            )

        return ChatbotResponseBuilder.needs_data(
            estado="ESPERANDO_DATOS_REPROGRAMACION",
            respuesta="¿Para qué nueva fecha y hora deseas reprogramar la cita?",
            faltan=["fecha_programada", "hora_inicio"],
            data={"id_cita": cita.id_cita},
        )

    @staticmethod
    def continuar_datos_reprogramacion(*, user, veterinaria_id, mensaje, contexto):
        from .intent_detector_service import IntentDetectorService

        data_ctx = contexto.get("data", {}) or {}
        id_cita = data_ctx.get("id_cita")

        if not id_cita:
            return ChatbotResponseBuilder.error(
                code="CITA_NO_VALIDA",
                respuesta="No pude validar la cita que deseas reprogramar.",
            )

        interpretacion = IntentDetectorService.detectar_intencion(mensaje)
        datos = interpretacion.get("datos", {}) or {}

        fecha_programada = datos.get("fecha_programada") or data_ctx.get("fecha_programada")
        hora_inicio = datos.get("hora_inicio") or data_ctx.get("hora_inicio")

        return ChatbotReprogramarService._resolver_reprogramacion(
            user=user,
            veterinaria_id=veterinaria_id,
            id_cita=id_cita,
            fecha_programada=fecha_programada,
            hora_inicio=hora_inicio,
        )

    @staticmethod
    def continuar_seleccion_horario_reprogramacion(*, user, veterinaria_id, mensaje, contexto):
        opcion = ChatbotSelectionResolverService.resolver_opcion_por_mensaje(
            mensaje=mensaje,
            opciones=contexto.get("opciones", []),
        )

        if not opcion:
            return ChatbotSelectionResolverService.respuesta_no_entendida(
                contexto=contexto
            )

        data = contexto.get("data", {}) or {}
        id_cita = data.get("id_cita")
        fecha_programada = data.get("fecha_programada")
        hora_inicio = opcion.get("hora_inicio")

        return ChatbotReprogramarService._resolver_reprogramacion(
            user=user,
            veterinaria_id=veterinaria_id,
            id_cita=id_cita,
            fecha_programada=fecha_programada,
            hora_inicio=hora_inicio,
        )

    @staticmethod
    def continuar_confirmacion_reprogramar_cita(*, user, veterinaria_id, mensaje, contexto):
        if ChatbotReprogramarService._usuario_cancela(mensaje):
            return ChatbotResponseBuilder.success(
                accion="REPROGRAMACION_ABORTADA",
                respuesta="De acuerdo, mantendré la cita con su fecha y hora actual.",
                data={},
                contexto=None,
            )

        if not ChatbotReprogramarService._usuario_confirma(mensaje):
            return ChatbotResponseBuilder.needs_confirmation(
                estado="ESPERANDO_CONFIRMACION_REPROGRAMAR_CITA",
                respuesta=(
                    "No pude identificar tu confirmación. "
                    "Responde sí para reprogramar o no para mantener la cita actual."
                ),
                data=contexto.get("data", {}),
            )

        data = contexto.get("data", {}) or {}
        id_cita = data.get("id_cita")
        fecha_programada = data.get("fecha_programada")
        hora_inicio = data.get("hora_inicio")
        hora_fin = data.get("hora_fin")

        if not id_cita:
            return ChatbotResponseBuilder.error(
                code="CITA_NO_VALIDA",
                respuesta="No pude validar la cita seleccionada.",
            )

        cita = ChatbotCitaSelector.obtener_cita_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
            id_cita=id_cita,
        )

        error_cita = ChatbotReprogramarService._validar_cita_reprogramable(cita)
        if error_cita:
            return error_cita

        nueva_fecha = ChatbotTimeUtils.to_date(fecha_programada)
        nueva_hora_inicio = ChatbotTimeUtils.to_time(hora_inicio)
        nueva_hora_fin = ChatbotTimeUtils.to_time(hora_fin)

        if not nueva_fecha or not nueva_hora_inicio or not nueva_hora_fin:
            return ChatbotResponseBuilder.error(
                code="FECHA_HORA_INVALIDA",
                respuesta="La nueva fecha u hora no tiene un formato válido.",
                data={"payload": data},
            )

        try:
            cita = CitaService.reprogramar_cita(
                cita,
                nueva_fecha,
                nueva_hora_inicio,
                nueva_hora_fin,
            )
        except Exception as exc:
            error_text = str(exc)

            if (
                "CONFLICTO_HORARIO" in error_text
                or "horario solicitado ya esta ocupado" in error_text
                or "horario solicitado ya está ocupado" in error_text
            ):
                return ChatbotReprogramarService._responder_conflicto_con_horarios(
                    veterinaria_id=veterinaria_id,
                    cita=cita,
                    fecha_programada=nueva_fecha,
                    data={
                        "id_cita": cita.id_cita,
                        "fecha_programada": nueva_fecha.isoformat(),
                    },
                )

            return ChatbotResponseBuilder.error(
                code="ERROR_REPROGRAMAR_CITA",
                respuesta="No pude reprogramar la cita por un error inesperado.",
                data={"error": error_text},
            )

        return ChatbotResponseBuilder.success(
            accion="CITA_REPROGRAMADA",
            respuesta=(
                "Listo, tu cita fue reprogramada correctamente para "
                f"{cita.fecha_programada} a las {cita.hora_inicio.strftime('%H:%M')}."
            ),
            data={
                "cita": CitaSerializer(cita).data,
            },
            contexto=None,
        )
