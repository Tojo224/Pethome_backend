from .chatbot_response_builder import ChatbotResponseBuilder
from .chatbot_selection_resolver_service import ChatbotSelectionResolverService

from ..selectors.chatbot_cita_selector import ChatbotCitaSelector
from ..utils.text_matcher import TextMatcher

from ...models.citas import Cita
from ...services.citas_service import CitaService
from ...serializers.citas_serializer import CitaSerializer


class ChatbotCancelarService:
    @staticmethod
    def _enumerar_opciones(opciones):
        opciones_enumeradas = []

        for index, opcion in enumerate(opciones, start=1):
            opcion_con_numero = dict(opcion)
            opcion_con_numero["numero"] = index
            opciones_enumeradas.append(opcion_con_numero)

        return opciones_enumeradas

    @staticmethod
    def _normalizar_motivo(motivo):
        motivo_limpio = str(motivo or "").strip()
        return motivo_limpio or None

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

        lineas.append("\nEscribe el número de la cita que deseas cancelar.")
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
            "cancelar",
            "cancela",
        ]

        return any(TextMatcher.normalize(palabra) in texto for palabra in afirmaciones)

    @staticmethod
    def _usuario_cancela(mensaje):
        texto = TextMatcher.normalize(mensaje)

        negaciones = [
            "no",
            "mejor no",
            "mantener",
            "no cancelar",
            "cancelar operacion",
            "cancelar operación",
            "detener",
        ]

        return any(TextMatcher.normalize(palabra) in texto for palabra in negaciones)

    @staticmethod
    def _error_cita_no_valida():
        return ChatbotResponseBuilder.error(
            code="CITA_NO_VALIDA",
            respuesta=(
                "No pude validar la cita seleccionada. "
                "Verifica tus citas activas e inténtalo nuevamente."
            ),
        )

    @staticmethod
    def _validar_cita_cancelable(cita):
        if not cita:
            return ChatbotCancelarService._error_cita_no_valida()

        if cita.estado == Cita.EstadoChoices.CANCELADA:
            return ChatbotResponseBuilder.error(
                code="CITA_YA_CANCELADA",
                respuesta="La cita seleccionada ya está cancelada.",
            )

        if cita.estado == Cita.EstadoChoices.COMPLETADA:
            return ChatbotResponseBuilder.error(
                code="CITA_COMPLETADA_NO_CANCELABLE",
                respuesta="No se puede cancelar una cita que ya está completada.",
            )

        if cita.estado not in [
            Cita.EstadoChoices.PENDIENTE,
            Cita.EstadoChoices.CONFIRMADA,
        ]:
            return ChatbotResponseBuilder.error(
                code="CITA_NO_VALIDA",
                respuesta="La cita seleccionada no se puede cancelar en su estado actual.",
            )

        return None

    @staticmethod
    def _respuesta_confirmacion_cancelacion(*, cita, motivo_cancelacion):
        mascota_nombre = getattr(getattr(cita, "mascota", None), "nombre", "Mascota")
        servicio_nombre = getattr(getattr(cita, "servicio", None), "nombre", "Servicio")
        fecha = cita.fecha_programada.isoformat() if cita.fecha_programada else ""
        hora = cita.hora_inicio.strftime("%H:%M") if cita.hora_inicio else ""

        return (
            f"¿Confirmas que deseas cancelar la cita de {mascota_nombre} "
            f"para {servicio_nombre} el {fecha} a las {hora}?\n"
            f"Motivo: {motivo_cancelacion}\n\n"
            "Responde sí para cancelar o no para mantener la cita."
        )

    @staticmethod
    def iniciar_cancelacion(*, user, veterinaria_id, interpretacion):
        datos = interpretacion.get("datos", {}) or {}
        motivo_cancelacion = ChatbotCancelarService._normalizar_motivo(
            datos.get("motivo_cancelacion")
        )

        citas_activas = list(
            ChatbotCitaSelector.listar_citas_activas_usuario(
                user=user,
                veterinaria_id=veterinaria_id,
            )
        )

        if not citas_activas:
            return ChatbotResponseBuilder.success(
                accion="SIN_CITAS_ACTIVAS",
                respuesta="No encontré citas activas para cancelar.",
                data={"citas": []},
                contexto=None,
            )

        if len(citas_activas) == 1:
            cita = citas_activas[0]
            id_cita = getattr(cita, "id_cita", None)

            if motivo_cancelacion:
                return ChatbotResponseBuilder.needs_confirmation(
                    estado="ESPERANDO_CONFIRMACION_CANCELAR_CITA",
                    respuesta=ChatbotCancelarService._respuesta_confirmacion_cancelacion(
                        cita=cita,
                        motivo_cancelacion=motivo_cancelacion,
                    ),
                    data={
                        "id_cita": id_cita,
                        "motivo_cancelacion": motivo_cancelacion,
                    },
                )

            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_MOTIVO_CANCELACION_CITA",
                respuesta=(
                    "Encontré esta cita activa:\n"
                    f"{ChatbotCancelarService._formatear_cita(cita)}.\n\n"
                    "¿Cuál es el motivo de la cancelación?"
                ),
                faltan=["motivo_cancelacion"],
                data={
                    "id_cita": id_cita,
                },
            )

        opciones = ChatbotCancelarService._enumerar_opciones(
            [
                ChatbotCitaSelector.to_option(cita)
                for cita in citas_activas
            ]
        )

        return ChatbotResponseBuilder.needs_selection(
            tipo="CITA",
            estado="ESPERANDO_SELECCION_CITA_CANCELAR",
            respuesta=ChatbotCancelarService._armar_respuesta_opciones_citas(opciones),
            opciones=opciones,
            data=(
                {"motivo_cancelacion": motivo_cancelacion}
                if motivo_cancelacion
                else {}
            ),
        )

    @staticmethod
    def continuar_seleccion_cita_cancelar(*, user, veterinaria_id, mensaje, contexto):
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

        error_validacion = ChatbotCancelarService._validar_cita_cancelable(cita)
        if error_validacion:
            return error_validacion

        data_contexto = contexto.get("data", {}) or {}
        motivo_cancelacion = ChatbotCancelarService._normalizar_motivo(
            data_contexto.get("motivo_cancelacion")
        )

        if motivo_cancelacion:
            return ChatbotResponseBuilder.needs_confirmation(
                estado="ESPERANDO_CONFIRMACION_CANCELAR_CITA",
                respuesta=ChatbotCancelarService._respuesta_confirmacion_cancelacion(
                    cita=cita,
                    motivo_cancelacion=motivo_cancelacion,
                ),
                data={
                    "id_cita": cita.id_cita,
                    "motivo_cancelacion": motivo_cancelacion,
                },
            )

        return ChatbotResponseBuilder.needs_data(
            estado="ESPERANDO_MOTIVO_CANCELACION_CITA",
            respuesta="¿Cuál es el motivo de la cancelación?",
            faltan=["motivo_cancelacion"],
            data={
                "id_cita": cita.id_cita,
            },
        )

    @staticmethod
    def continuar_motivo_cancelacion(*, user, veterinaria_id, mensaje, contexto):
        data = contexto.get("data", {}) or {}
        id_cita = data.get("id_cita")

        if not id_cita:
            return ChatbotCancelarService._error_cita_no_valida()

        cita = ChatbotCitaSelector.obtener_cita_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
            id_cita=id_cita,
        )

        error_validacion = ChatbotCancelarService._validar_cita_cancelable(cita)
        if error_validacion:
            return error_validacion

        motivo_cancelacion = ChatbotCancelarService._normalizar_motivo(mensaje)

        if not motivo_cancelacion:
            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_MOTIVO_CANCELACION_CITA",
                respuesta="Para cancelar la cita necesito que indiques el motivo de la cancelación.",
                faltan=["motivo_cancelacion"],
                data={
                    "id_cita": cita.id_cita,
                },
            )

        return ChatbotResponseBuilder.needs_confirmation(
            estado="ESPERANDO_CONFIRMACION_CANCELAR_CITA",
            respuesta=ChatbotCancelarService._respuesta_confirmacion_cancelacion(
                cita=cita,
                motivo_cancelacion=motivo_cancelacion,
            ),
            data={
                "id_cita": cita.id_cita,
                "motivo_cancelacion": motivo_cancelacion,
            },
        )

    @staticmethod
    def continuar_confirmacion_cancelar_cita(*, user, veterinaria_id, mensaje, contexto):
        if ChatbotCancelarService._usuario_cancela(mensaje):
            return ChatbotResponseBuilder.success(
                accion="CANCELACION_ABORTADA",
                respuesta="De acuerdo, mantendré la cita activa.",
                data={},
                contexto=None,
            )

        if not ChatbotCancelarService._usuario_confirma(mensaje):
            return ChatbotResponseBuilder.needs_confirmation(
                estado="ESPERANDO_CONFIRMACION_CANCELAR_CITA",
                respuesta=(
                    "No pude identificar tu confirmación. "
                    "Responde sí para cancelar o no para mantener la cita."
                ),
                data=contexto.get("data", {}),
            )

        data = contexto.get("data", {}) or {}
        id_cita = data.get("id_cita")
        motivo_cancelacion = ChatbotCancelarService._normalizar_motivo(
            data.get("motivo_cancelacion")
        )

        if not id_cita:
            return ChatbotCancelarService._error_cita_no_valida()

        if not motivo_cancelacion:
            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_MOTIVO_CANCELACION_CITA",
                respuesta="Para cancelar la cita necesito que indiques el motivo de la cancelación.",
                faltan=["motivo_cancelacion"],
                data={"id_cita": id_cita},
            )

        cita = ChatbotCitaSelector.obtener_cita_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
            id_cita=id_cita,
        )

        error_validacion = ChatbotCancelarService._validar_cita_cancelable(cita)
        if error_validacion:
            return error_validacion

        try:
            cita = CitaService.actualizar_estado(
                cita,
                Cita.EstadoChoices.CANCELADA,
                motivo_cancelacion,
            )
        except Exception as exc:
            return ChatbotResponseBuilder.error(
                code="ERROR_CANCELAR_CITA",
                respuesta="No pude cancelar la cita por un error inesperado.",
                data={"error": str(exc)},
            )

        return ChatbotResponseBuilder.success(
            accion="CITA_CANCELADA",
            respuesta="Listo, tu cita fue cancelada correctamente.",
            data={
                "cita": CitaSerializer(cita).data,
            },
            contexto=None,
        )
