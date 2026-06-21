from .intent_detector_service import IntentDetectorService
from .chatbot_agendar_service import ChatbotAgendarService
from .chatbot_cancelar_service import ChatbotCancelarService
from .chatbot_reprogramar_service import ChatbotReprogramarService
from .chatbot_response_builder import ChatbotResponseBuilder
from .chatbot_context_query_service import ChatbotContextQueryService
from .chatbot_info_service import ChatbotInfoService
from .chatbot_tienda_service import ChatbotTiendaService


class ChatbotOrchestratorService:
    @staticmethod
    def procesar_mensaje(*, user, veterinaria_id, mensaje, contexto=None):
        contexto = contexto or {}
        estado = contexto.get("estado")

        if str(estado or "").upper().startswith("TIENDA_"):
            return ChatbotTiendaService.procesar_mensaje(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado:
            consulta = ChatbotContextQueryService.detectar_consulta_apoyo(mensaje)

            if consulta == "SERVICIOS":
                return ChatbotInfoService.responder_servicios(
                    veterinaria_id=veterinaria_id,
                    contexto=contexto,
                )

            if consulta == "MASCOTAS":
                return ChatbotInfoService.responder_mascotas(
                    user=user,
                    veterinaria_id=veterinaria_id,
                    contexto=contexto,
                )

            if consulta == "PRECIOS":
                return ChatbotInfoService.responder_precios(
                    veterinaria_id=veterinaria_id,
                    mensaje=mensaje,
                    contexto=contexto,
                )

            if consulta == "MODALIDADES":
                return ChatbotInfoService.responder_modalidades(
                    contexto=contexto,
                )

        if estado == "ESPERANDO_SELECCION_CITA_CANCELAR":
            return ChatbotCancelarService.continuar_seleccion_cita_cancelar(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_MOTIVO_CANCELACION_CITA":
            return ChatbotCancelarService.continuar_motivo_cancelacion(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_CONFIRMACION_CANCELAR_CITA":
            return ChatbotCancelarService.continuar_confirmacion_cancelar_cita(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_SELECCION_CITA_REPROGRAMAR":
            return ChatbotReprogramarService.continuar_seleccion_cita_reprogramar(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_DATOS_REPROGRAMACION":
            return ChatbotReprogramarService.continuar_datos_reprogramacion(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_CONFIRMACION_REPROGRAMAR_CITA":
            return ChatbotReprogramarService.continuar_confirmacion_reprogramar_cita(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_SELECCION_HORARIO_REPROGRAMACION":
            return ChatbotReprogramarService.continuar_seleccion_horario_reprogramacion(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_DATOS_AGENDAMIENTO":
            return ChatbotAgendarService.continuar_datos_agendamiento(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_SELECCION_MASCOTA":
            return ChatbotAgendarService.continuar_seleccion_mascota(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_SELECCION_SERVICIO":
            return ChatbotAgendarService.continuar_seleccion_servicio(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_SELECCION_PRECIO_SERVICIO":
            return ChatbotAgendarService.continuar_seleccion_precio_servicio(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_SELECCION_HORARIO_AGENDAMIENTO":
            return ChatbotAgendarService.continuar_seleccion_horario(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == "ESPERANDO_CONFIRMACION_CREAR_CITA":
            return ChatbotAgendarService.continuar_confirmacion_crear_cita(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if ChatbotTiendaService.es_mensaje_tienda(mensaje, contexto):
            return ChatbotTiendaService.procesar_mensaje(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        interpretacion = IntentDetectorService.detectar_intencion(mensaje)
        intencion = str(interpretacion.get("intencion", "DESCONOCIDA")).upper()

        if intencion == "AGENDAR_CITA":
            return ChatbotAgendarService.preparar_agendamiento(
                user=user,
                veterinaria_id=veterinaria_id,
                interpretacion=interpretacion,
            )

        if intencion == "CANCELAR_CITA":
            return ChatbotCancelarService.iniciar_cancelacion(
                user=user,
                veterinaria_id=veterinaria_id,
                interpretacion=interpretacion,
            )

        if intencion == "REPROGRAMAR_CITA":
            return ChatbotReprogramarService.iniciar_reprogramacion(
                user=user,
                veterinaria_id=veterinaria_id,
                interpretacion=interpretacion,
            )

        if intencion == "LISTAR_SERVICIOS":
            return ChatbotResponseBuilder.success(
                accion="LISTAR_SERVICIOS_PENDIENTE",
                respuesta="Puedo ayudarte a listar los servicios disponibles.",
                data={
                    "interpretacion": interpretacion,
                },
            )

        if intencion == "LISTAR_CITAS":
            return ChatbotResponseBuilder.success(
                accion="LISTAR_CITAS_PENDIENTE",
                respuesta="Puedo ayudarte a consultar tus citas.",
                data={
                    "interpretacion": interpretacion,
                },
            )

        return ChatbotResponseBuilder.error(
            code="INTENCION_DESCONOCIDA",
            respuesta="No entendí exactamente qué deseas hacer con tus citas.",
            data={
                "interpretacion": interpretacion,
            },
        )
