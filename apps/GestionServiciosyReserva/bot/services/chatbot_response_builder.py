class ChatbotResponseBuilder:
    @staticmethod
    def success(*, respuesta, accion=None, data=None, contexto=None):
        return {
            "ok": True,
            "accion": accion,
            "respuesta": respuesta,
            "data": data or {},
            "contexto": contexto,
        }

    @staticmethod
    def needs_data(*, respuesta, faltan=None, opciones=None, data=None, contexto=None, estado=None):
        if contexto is None and estado:
            contexto = {
                "accion_anterior": "FALTAN_DATOS",
                "estado": estado,
                "faltan": faltan or [],
                "data": data or {},
            }

        return {
            "ok": False,
            "accion": "FALTAN_DATOS",
            "estado": estado,
            "respuesta": respuesta,
            "faltan": faltan or [],
            "opciones": opciones or [],
            "data": data or {},
            "contexto": contexto,
        }

    @staticmethod
    def needs_selection(*, respuesta, tipo, estado, opciones, data=None):
        contexto = {
            "accion_anterior": "REQUIERE_SELECCION",
            "estado": estado,
            "tipo_anterior": tipo,
            "opciones": opciones or [],
            "data": data or {},
        }

        return {
            "ok": False,
            "accion": "REQUIERE_SELECCION",
            "estado": estado,
            "tipo": tipo,
            "respuesta": respuesta,
            "opciones": opciones or [],
            "data": data or {},
            "contexto": contexto,
        }

    @staticmethod
    def error(*, respuesta, code="CHATBOT_ERROR", data=None, contexto=None):
        return {
            "ok": False,
            "accion": "ERROR",
            "code": code,
            "respuesta": respuesta,
            "data": data or {},
            "contexto": contexto,
        }
    
    @staticmethod
    def needs_confirmation(*, respuesta, estado, data=None):
        contexto = {
            "accion_anterior": "REQUIERE_CONFIRMACION",
            "estado": estado,
            "data": data or {},
        }

        return {
            "ok": False,
            "accion": "REQUIERE_CONFIRMACION",
            "estado": estado,
            "respuesta": respuesta,
            "data": data or {},
            "contexto": contexto,
        }