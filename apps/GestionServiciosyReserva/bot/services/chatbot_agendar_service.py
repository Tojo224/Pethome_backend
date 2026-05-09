from datetime import datetime, timedelta
import re

from django.utils import timezone

from .chatbot_response_builder import ChatbotResponseBuilder
from .chatbot_selection_resolver_service import ChatbotSelectionResolverService

from ..selectors.chatbot_mascota_selector import ChatbotMascotaSelector
from ..selectors.chatbot_servicio_selector import ChatbotServicioSelector
from ..selectors.chatbot_precio_selector import ChatbotPrecioSelector

from ..utils.time_utils import ChatbotTimeUtils
from ..utils.text_matcher import TextMatcher

from ...models.citas import Cita
from ...services.citas_service import CitaService
from ...serializers.citas_serializer import CitaSerializer


class ChatbotAgendarService:
    @staticmethod
    def _normalizar_direccion(direccion):
        direccion_limpia = str(direccion or "").strip()
        coordenadas = re.search(
            r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)",
            direccion_limpia,
        )
        if coordenadas:
            return f"{coordenadas.group(1)}, {coordenadas.group(2)}"
        return direccion_limpia or None

    @staticmethod
    def _direccion_compartida_desde_contexto(contexto):
        if not isinstance(contexto, dict):
            return None

        direccion = ChatbotAgendarService._normalizar_direccion(
            contexto.get("direccion_cita_compartida")
        )
        if direccion:
            return direccion

        ubicacion = contexto.get("ubicacion_actual")
        if isinstance(ubicacion, dict):
            direccion = ChatbotAgendarService._normalizar_direccion(
                ubicacion.get("direccion")
            )
            if direccion:
                return direccion

            latitud = ubicacion.get("latitud") or ubicacion.get("latitude")
            longitud = ubicacion.get("longitud") or ubicacion.get("longitude")
            if latitud is not None and longitud is not None:
                return f"{latitud}, {longitud}"

        return None

    @staticmethod
    def _mensaje_es_ubicacion_compartida(mensaje):
        texto = TextMatcher.normalize(mensaje)
        return "comparto mi ubicacion" in texto or "ubicacion actual" in texto

    @staticmethod
    def _aplicar_reglas_direccion_por_modalidad(datos):
        datos_finales = dict(datos or {})
        modalidad = str(datos_finales.get("modalidad") or "").strip().upper()
        direccion_cita = ChatbotAgendarService._normalizar_direccion(
            datos_finales.get("direccion_cita")
        )

        if modalidad == "CLINICA":
            datos_finales["direccion_cita"] = None
        elif modalidad == "DOMICILIO":
            datos_finales["direccion_cita"] = direccion_cita

        return datos_finales

    @staticmethod
    def _enumerar_opciones(opciones):
        opciones_enumeradas = []

        for index, opcion in enumerate(opciones, start=1):
            opcion_con_numero = dict(opcion)
            opcion_con_numero["numero"] = index
            opciones_enumeradas.append(opcion_con_numero)

        return opciones_enumeradas

    @staticmethod
    def _armar_respuesta_opciones_servicio(opciones):
        lineas = [
            "Encontré varios servicios parecidos. Escribe el número o el nombre del servicio que deseas:"
        ]

        for opcion in opciones:
            lineas.append(f"{opcion.get('numero')}. {opcion.get('nombre')}")

        return "\n".join(lineas)

    @staticmethod
    def _humanizar_faltantes(faltan):
        etiquetas = {
            "mascota_nombre": "nombre de la mascota",
            "servicio_nombre": "servicio",
            "fecha_programada": "fecha",
            "hora_inicio": "hora",
            "modalidad": "modalidad",
            "direccion_cita": "dirección del domicilio",
        }

        faltan = list(faltan or [])
        faltantes_humanos = [etiquetas.get(campo, campo) for campo in faltan]

        if not faltantes_humanos:
            return ""

        if len(faltantes_humanos) == 1:
            return faltantes_humanos[0]

        if len(faltantes_humanos) == 2:
            return f"{faltantes_humanos[0]} y {faltantes_humanos[1]}"

        return f"{', '.join(faltantes_humanos[:-1])} y {faltantes_humanos[-1]}"

    @staticmethod
    def _mensaje_faltantes_agendamiento(faltan):
        faltan_lista = list(faltan or [])
        faltan = set(faltan_lista)

        if faltan == {"modalidad"}:
            return (
                "Para agendar la cita me falta la modalidad. "
                "¿Deseas atención en clínica o a domicilio?"
            )

        if faltan == {"direccion_cita"}:
            return (
                "Para agendar la cita a domicilio me falta la dirección. "
                "¿A qué dirección debemos acudir?"
            )

        if faltan == {"mascota_nombre"}:
            return (
                "Para agendar la cita me falta el nombre de la mascota. "
                "¿Para cuál mascota deseas agendar?"
            )

        if faltan == {"servicio_nombre"}:
            return (
                "Para agendar la cita me falta el servicio que necesitas. "
                "¿Qué servicio deseas reservar?"
            )

        if faltan == {"fecha_programada"}:
            return (
                "Para agendar la cita me falta la fecha. "
                "¿Para qué día deseas agendar?"
            )

        if faltan == {"hora_inicio"}:
            return (
                "Para agendar la cita me falta la hora. "
                "¿A qué hora prefieres la cita?"
            )

        if faltan == {"fecha_programada", "hora_inicio"}:
            return (
                "Para agendar la cita me faltan la fecha y la hora. "
                "¿Qué día y a qué hora prefieres?"
            )

        faltantes_humanos = ChatbotAgendarService._humanizar_faltantes(faltan_lista)
        return (
            f"Para agendar la cita me faltan estos datos: {faltantes_humanos}. "
            "Indícame esos datos para continuar."
        )

    @staticmethod
    def _mensaje_fecha_invalida_agendamiento(*, tipo, faltan):
        faltan = list(faltan or [])

        if tipo == "HORA_PASADA":
            base = "No puedo agendar citas en horarios pasados. Indícame una hora futura"
            campo_principal = "hora_inicio"
        else:
            base = "No puedo agendar citas en fechas pasadas. Indícame una fecha futura"
            campo_principal = "fecha_programada"

        faltantes_extra = [campo for campo in faltan if campo != campo_principal]

        if not faltantes_extra:
            return f"{base} para continuar."

        if faltantes_extra == ["direccion_cita"]:
            return f"{base} y la dirección del domicilio para continuar."

        extras_humanos = ChatbotAgendarService._humanizar_faltantes(faltantes_extra)
        return f"{base} y estos datos: {extras_humanos}, para continuar."

    @staticmethod
    def _validar_fecha_hora_agendamiento(interpretacion):
        interpretacion = ChatbotAgendarService._recalcular_faltantes_agendamiento(
            interpretacion
        )
        datos = interpretacion.get("datos", {}) or {}
        faltan = list(interpretacion.get("faltan", []) or [])

        modalidad = str(datos.get("modalidad") or "").strip().upper()
        direccion_cita = ChatbotAgendarService._normalizar_direccion(
            datos.get("direccion_cita")
        )

        if modalidad == "DOMICILIO" and not direccion_cita and "direccion_cita" not in faltan:
            faltan.append("direccion_cita")

        fecha_invalida = bool(datos.get("fecha_invalida"))
        motivo_fecha_invalida = str(datos.get("motivo_fecha_invalida") or "")
        motivo_norm = TextMatcher.normalize(motivo_fecha_invalida)

        if fecha_invalida:
            if "fecha_programada" not in faltan:
                faltan.append("fecha_programada")
            if not datos.get("hora_inicio") and "hora_inicio" not in faltan:
                faltan.append("hora_inicio")

            tipo = "HORA_PASADA" if "hora" in motivo_norm else "FECHA_PASADA"

            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_AGENDAMIENTO",
                respuesta=ChatbotAgendarService._mensaje_fecha_invalida_agendamiento(
                    tipo=tipo,
                    faltan=faltan,
                ),
                faltan=faltan,
                data={
                    "interpretacion": interpretacion,
                },
            )

        fecha_programada = ChatbotTimeUtils.to_date(datos.get("fecha_programada"))
        hora_inicio = ChatbotTimeUtils.to_time(datos.get("hora_inicio"))

        if not fecha_programada:
            return None

        hoy = timezone.localdate()
        ahora = timezone.localtime()

        if fecha_programada < hoy:
            if "fecha_programada" not in faltan:
                faltan.append("fecha_programada")

            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_AGENDAMIENTO",
                respuesta=ChatbotAgendarService._mensaje_fecha_invalida_agendamiento(
                    tipo="FECHA_PASADA",
                    faltan=faltan,
                ),
                faltan=faltan,
                data={
                    "interpretacion": interpretacion,
                },
            )

        if fecha_programada == hoy and hora_inicio and hora_inicio <= ahora.time():
            if "hora_inicio" not in faltan:
                faltan.append("hora_inicio")

            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_AGENDAMIENTO",
                respuesta=ChatbotAgendarService._mensaje_fecha_invalida_agendamiento(
                    tipo="HORA_PASADA",
                    faltan=faltan,
                ),
                faltan=faltan,
                data={
                    "interpretacion": interpretacion,
                },
            )

        return None

    @staticmethod
    def _detectar_modalidad_desde_texto(mensaje):
        texto = TextMatcher.normalize(mensaje)

        if any(
            palabra in texto
            for palabra in [
                "domicilio",
                "a domicilio",
                "en mi casa",
                "mi casa",
                "casa",
            ]
        ):
            return "DOMICILIO"

        if any(
            palabra in texto
            for palabra in [
                "clinica",
                "en clinica",
                "veterinaria",
                "en la veterinaria",
                "local",
                "en el local",
            ]
        ):
            return "CLINICA"

        return None

    @staticmethod
    def _obtener_duracion_valida(servicio):
        duracion = getattr(servicio, "duracion_estimada", None)

        try:
            duracion = int(duracion)
        except (TypeError, ValueError):
            return None

        if duracion <= 0:
            return None

        return duracion

    @staticmethod
    def _recalcular_faltantes_agendamiento(interpretacion):
        datos = ChatbotAgendarService._aplicar_reglas_direccion_por_modalidad(
            interpretacion.get("datos", {}) or {}
        )

        faltan = []

        if not datos.get("mascota_nombre"):
            faltan.append("mascota_nombre")

        if not datos.get("servicio_nombre"):
            faltan.append("servicio_nombre")

        if not datos.get("fecha_programada"):
            faltan.append("fecha_programada")

        if not datos.get("hora_inicio"):
            faltan.append("hora_inicio")

        if not datos.get("modalidad"):
            faltan.append("modalidad")
        elif str(datos.get("modalidad") or "").strip().upper() == "DOMICILIO":
            tiene_direccion = ChatbotAgendarService._normalizar_direccion(
                datos.get("direccion_cita")
            )
            if not tiene_direccion:
                faltan.append("direccion_cita")

        interpretacion["datos"] = datos
        interpretacion["faltan"] = faltan
        return interpretacion

    @staticmethod
    def _merge_interpretaciones_agendamiento(
        interpretacion_anterior,
        interpretacion_nueva,
    ):
        datos_anteriores = interpretacion_anterior.get("datos", {}) or {}
        datos_nuevos = interpretacion_nueva.get("datos", {}) or {}

        datos_finales = dict(datos_anteriores)

        for campo, valor in datos_nuevos.items():
            if valor not in [None, ""]:
                datos_finales[campo] = valor

        datos_finales = ChatbotAgendarService._aplicar_reglas_direccion_por_modalidad(
            datos_finales
        )

        interpretacion_final = dict(interpretacion_anterior)
        interpretacion_final["intencion"] = "AGENDAR_CITA"
        interpretacion_final["datos"] = datos_finales
        interpretacion_final["respuesta"] = "Verificaremos la información antes de confirmar la cita."

        return ChatbotAgendarService._recalcular_faltantes_agendamiento(
            interpretacion_final
        )

    @staticmethod
    def _completar_faltantes_desde_mensaje(interpretacion, mensaje, faltan, contexto=None):
        interpretacion_final = dict(interpretacion or {})
        datos = dict(interpretacion_final.get("datos", {}) or {})

        faltan = faltan or []
        mensaje_limpio = str(mensaje or "").strip()

        if "modalidad" in faltan:
            modalidad = ChatbotAgendarService._detectar_modalidad_desde_texto(
                mensaje_limpio
            )
            if modalidad:
                datos["modalidad"] = modalidad

        if len(faltan) == 1 and "direccion_cita" in faltan and mensaje_limpio:
            direccion_compartida = ChatbotAgendarService._direccion_compartida_desde_contexto(
                contexto
            )
            if (
                direccion_compartida
                and ChatbotAgendarService._mensaje_es_ubicacion_compartida(mensaje_limpio)
            ):
                datos["direccion_cita"] = direccion_compartida
            else:
                datos["direccion_cita"] = mensaje_limpio

        if len(faltan) == 1 and "mascota_nombre" in faltan and mensaje_limpio:
            datos["mascota_nombre"] = mensaje_limpio

        if len(faltan) == 1 and "servicio_nombre" in faltan and mensaje_limpio:
            datos["servicio_nombre"] = mensaje_limpio

        interpretacion_final["intencion"] = "AGENDAR_CITA"
        interpretacion_final["datos"] = (
            ChatbotAgendarService._aplicar_reglas_direccion_por_modalidad(datos)
        )
        interpretacion_final["respuesta"] = "Verificaremos la información antes de confirmar la cita."

        return ChatbotAgendarService._recalcular_faltantes_agendamiento(
            interpretacion_final
        )

    @staticmethod
    def _obtener_horarios_disponibles(
        *,
        veterinaria_id,
        fecha_programada,
        modalidad,
        duracion_minutos,
        cantidad=6,
    ):
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

        # Importante:
        # No filtramos por modalidad para mantener coherencia con CitaService.crear_cita().
        # Si cualquier cita activa ocupa ese horario, no se muestra como disponible.
        citas_ocupadas = Cita.objects.filter(
            veterinaria_id=veterinaria_id,
            fecha_programada=fecha_programada,
            estado__in=[
                Cita.EstadoChoices.PENDIENTE,
                Cita.EstadoChoices.CONFIRMADA,
            ],
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

            ocupado = False

            for cita in citas_ocupadas:
                cita_inicio = datetime.combine(cita.fecha_programada, cita.hora_inicio)
                cita_fin = datetime.combine(cita.fecha_programada, cita.hora_fin)

                if actual < cita_fin and fin_slot > cita_inicio:
                    ocupado = True
                    break

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
    def _responder_conflicto_con_horarios(
        *,
        veterinaria_id,
        fecha_programada,
        modalidad,
        servicio,
        data,
    ):
        duracion = ChatbotAgendarService._obtener_duracion_valida(servicio)

        if not duracion:
            return ChatbotResponseBuilder.error(
                code="DURACION_SERVICIO_INVALIDA",
                respuesta=(
                    "El servicio seleccionado no tiene una duración válida configurada. "
                    "No puedo sugerir horarios automáticamente."
                ),
                data=data,
            )

        horarios = ChatbotAgendarService._obtener_horarios_disponibles(
            veterinaria_id=veterinaria_id,
            fecha_programada=fecha_programada,
            modalidad=modalidad,
            duracion_minutos=duracion,
        )

        if not horarios:
            return ChatbotResponseBuilder.error(
                code="SIN_HORARIOS_DISPONIBLES",
                respuesta=(
                    "Ese horario ya está ocupado y no encontré otros horarios disponibles "
                    "para esa fecha. Indícame otra fecha u hora."
                ),
                data=data,
                contexto={
                    "accion_anterior": "FALTAN_DATOS",
                    "estado": "ESPERANDO_DATOS_AGENDAMIENTO",
                    "faltan": ["fecha_programada", "hora_inicio"],
                    "data": data,
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
            estado="ESPERANDO_SELECCION_HORARIO_AGENDAMIENTO",
            respuesta="\n".join(lineas),
            opciones=horarios,
            data=data,
        )

    @staticmethod
    def _resolver_precio_y_payload(
        *,
        user,
        veterinaria_id,
        interpretacion,
        mascota,
        servicio,
    ):
        datos = interpretacion.get("datos", {}) or {}

        fecha_programada = datos.get("fecha_programada")
        hora_inicio = datos.get("hora_inicio")
        modalidad = str(datos.get("modalidad") or "").strip().upper()
        direccion_cita = ChatbotAgendarService._normalizar_direccion(
            datos.get("direccion_cita")
        )
        if modalidad == "CLINICA":
            direccion_cita = None

        if modalidad == "DOMICILIO" and not direccion_cita:
            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_AGENDAMIENTO",
                respuesta="¿A qué dirección debemos acudir para la cita a domicilio?",
                faltan=["direccion_cita"],
                data={
                    "interpretacion": interpretacion,
                },
            )

        if modalidad == "DOMICILIO" and not servicio.disponible_domicilio:
            return ChatbotResponseBuilder.error(
                code="SERVICIO_NO_DISPONIBLE_DOMICILIO",
                respuesta=(
                    f"El servicio '{servicio.nombre}' no está disponible a domicilio. "
                    "Puedes elegir modalidad clínica u otro servicio."
                ),
                data={
                    "id_servicio": servicio.id_servicio,
                    "servicio_nombre": servicio.nombre,
                },
            )

        duracion = ChatbotAgendarService._obtener_duracion_valida(servicio)
        if not duracion:
            return ChatbotResponseBuilder.error(
                code="DURACION_SERVICIO_INVALIDA",
                respuesta=(
                    f"El servicio '{servicio.nombre}' no tiene una duración válida configurada. "
                    "No puedo agendarlo automáticamente."
                ),
                data={
                    "id_servicio": servicio.id_servicio,
                    "servicio_nombre": servicio.nombre,
                    "duracion_estimada": getattr(servicio, "duracion_estimada", None),
                },
            )

        precios = ChatbotPrecioSelector.listar_por_servicio_y_modalidad(
            veterinaria_id=veterinaria_id,
            servicio_id=servicio.id_servicio,
            modalidad=modalidad,
        )

        if not precios:
            return ChatbotResponseBuilder.error(
                code="PRECIO_NO_ENCONTRADO",
                respuesta=(
                    f"No encontré un precio activo para '{servicio.nombre}' "
                    f"en modalidad {modalidad}."
                ),
                data={
                    "id_servicio": servicio.id_servicio,
                    "servicio_nombre": servicio.nombre,
                    "modalidad": modalidad,
                },
            )

        if len(precios) > 1:
            opciones = ChatbotAgendarService._enumerar_opciones(
                [
                    ChatbotPrecioSelector.to_option(precio)
                    for precio in precios
                ]
            )

            return ChatbotResponseBuilder.needs_selection(
                tipo="PRECIO_SERVICIO",
                estado="ESPERANDO_SELECCION_PRECIO_SERVICIO",
                respuesta=(
                    "Encontré varias opciones de precio. "
                    "Escribe el número de la opción que deseas."
                ),
                opciones=opciones,
                data={
                    "interpretacion": interpretacion,
                    "id_mascota": getattr(mascota, "id_mascota", None),
                    "id_servicio": servicio.id_servicio,
                    "modalidad": modalidad,
                },
            )

        precio = precios[0]
        hora_inicio_normalizada = ChatbotTimeUtils.normalize_time(hora_inicio)

        payload_crear_cita = {
            "mascota": getattr(mascota, "id_mascota", None),
            "servicio": servicio.id_servicio,
            "precio_servicio": precio.id_precio,
            "fecha_programada": fecha_programada,
            "hora_inicio": hora_inicio_normalizada,
            "modalidad": modalidad,
            "direccion_cita": direccion_cita,
            "descripcion": "Cita preparada desde chatbot IA.",
        }

        linea_direccion = ""
        if modalidad == "DOMICILIO":
            linea_direccion = f"Dirección: {direccion_cita}\n"

        return ChatbotResponseBuilder.needs_confirmation(
            estado="ESPERANDO_CONFIRMACION_CREAR_CITA",
            respuesta=(
                f"Ya tengo los datos para agendar la cita:\n"
                f"Mascota: {getattr(mascota, 'nombre', '')}\n"
                f"Servicio: {servicio.nombre}\n"
                f"Fecha: {fecha_programada}\n"
                f"Hora: {hora_inicio_normalizada}\n"
                f"Modalidad: {modalidad}\n"
                f"{linea_direccion}"
                f"Precio: {precio.precio} Bs\n\n"
                "¿Confirmas que deseas agendar esta cita? Responde sí o no."
            ),
            data={
                "interpretacion": interpretacion,
                "mascota": ChatbotMascotaSelector.to_option(mascota),
                "servicio": ChatbotServicioSelector.to_option(servicio),
                "precio": ChatbotPrecioSelector.to_option(precio),
                "payload_crear_cita": payload_crear_cita,
            },
        )

    @staticmethod
    def preparar_agendamiento(*, user, veterinaria_id, interpretacion):
        interpretacion = ChatbotAgendarService._recalcular_faltantes_agendamiento(
            interpretacion
        )

        datos = interpretacion.get("datos", {}) or {}

        mascota_nombre = datos.get("mascota_nombre")
        servicio_nombre = datos.get("servicio_nombre")
        fecha_programada = datos.get("fecha_programada")
        hora_inicio = datos.get("hora_inicio")
        modalidad = datos.get("modalidad")
        direccion_cita = ChatbotAgendarService._normalizar_direccion(
            datos.get("direccion_cita")
        )

        faltan = []

        if not mascota_nombre:
            faltan.append("mascota_nombre")

        if not servicio_nombre:
            faltan.append("servicio_nombre")

        if not fecha_programada:
            faltan.append("fecha_programada")

        if not hora_inicio:
            faltan.append("hora_inicio")

        if not modalidad:
            faltan.append("modalidad")
        elif str(modalidad).strip().upper() == "DOMICILIO" and not direccion_cita:
            faltan.append("direccion_cita")

        validacion_fecha_hora = ChatbotAgendarService._validar_fecha_hora_agendamiento(
            interpretacion
        )
        if validacion_fecha_hora:
            return validacion_fecha_hora

        if faltan:
            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_AGENDAMIENTO",
                respuesta=ChatbotAgendarService._mensaje_faltantes_agendamiento(faltan),
                faltan=faltan,
                data={
                    "interpretacion": interpretacion,
                },
            )

        mascotas_match = ChatbotMascotaSelector.buscar_por_nombre(
            user=user,
            veterinaria_id=veterinaria_id,
            nombre=mascota_nombre,
        )

        if not mascotas_match:
            mascotas = ChatbotMascotaSelector.listar_mascotas_usuario(
                user=user,
                veterinaria_id=veterinaria_id,
            )

            opciones = ChatbotAgendarService._enumerar_opciones(
                [
                    ChatbotMascotaSelector.to_option(mascota)
                    for mascota in mascotas
                ]
            )

            return ChatbotResponseBuilder.needs_selection(
                tipo="MASCOTA",
                estado="ESPERANDO_SELECCION_MASCOTA",
                respuesta=(
                    f"No encontré una mascota llamada '{mascota_nombre}'. "
                    "Escribe el número o nombre de una de tus mascotas registradas."
                ),
                opciones=opciones,
                data={
                    "interpretacion": interpretacion,
                },
            )

        if len(mascotas_match) > 1:
            opciones = ChatbotAgendarService._enumerar_opciones(
                [
                    ChatbotMascotaSelector.to_option(match["item"])
                    for match in mascotas_match
                ]
            )

            return ChatbotResponseBuilder.needs_selection(
                tipo="MASCOTA",
                estado="ESPERANDO_SELECCION_MASCOTA",
                respuesta=(
                    "Encontré varias mascotas parecidas. "
                    "Escribe el número o nombre de la mascota."
                ),
                opciones=opciones,
                data={
                    "interpretacion": interpretacion,
                },
            )

        mascota = mascotas_match[0]["item"]

        servicios_match = ChatbotServicioSelector.buscar_por_nombre(
            veterinaria_id=veterinaria_id,
            nombre=servicio_nombre,
        )

        if not servicios_match:
            servicios = ChatbotServicioSelector.listar_servicios_activos(
                veterinaria_id=veterinaria_id
            )

            opciones = ChatbotAgendarService._enumerar_opciones(
                [
                    ChatbotServicioSelector.to_option(servicio)
                    for servicio in servicios
                ]
            )

            return ChatbotResponseBuilder.needs_selection(
                tipo="SERVICIO",
                estado="ESPERANDO_SELECCION_SERVICIO",
                respuesta=(
                    f"No encontré un servicio relacionado con '{servicio_nombre}'. "
                    "Escribe el número o nombre de uno de los servicios disponibles."
                ),
                opciones=opciones,
                data={
                    "interpretacion": interpretacion,
                    "id_mascota": getattr(mascota, "id_mascota", None),
                },
            )

        if len(servicios_match) > 1:
            opciones = ChatbotAgendarService._enumerar_opciones(
                [
                    ChatbotServicioSelector.to_option(match["item"])
                    for match in servicios_match
                ]
            )

            respuesta = ChatbotAgendarService._armar_respuesta_opciones_servicio(opciones)

            return ChatbotResponseBuilder.needs_selection(
                tipo="SERVICIO",
                estado="ESPERANDO_SELECCION_SERVICIO",
                respuesta=respuesta,
                opciones=opciones,
                data={
                    "interpretacion": interpretacion,
                    "id_mascota": getattr(mascota, "id_mascota", None),
                },
            )

        servicio = servicios_match[0]["item"]

        return ChatbotAgendarService._resolver_precio_y_payload(
            user=user,
            veterinaria_id=veterinaria_id,
            interpretacion=interpretacion,
            mascota=mascota,
            servicio=servicio,
        )

    @staticmethod
    def continuar_datos_agendamiento(*, user, veterinaria_id, mensaje, contexto):
        from .intent_detector_service import IntentDetectorService

        data = contexto.get("data", {}) or {}
        interpretacion_anterior = data.get("interpretacion", {}) or {}
        faltan_contexto = contexto.get("faltan") or interpretacion_anterior.get("faltan", [])

        interpretacion_directa = ChatbotAgendarService._completar_faltantes_desde_mensaje(
            interpretacion_anterior,
            mensaje,
            faltan_contexto,
            contexto,
        )

        if not interpretacion_directa.get("faltan"):
            return ChatbotAgendarService.preparar_agendamiento(
                user=user,
                veterinaria_id=veterinaria_id,
                interpretacion=interpretacion_directa,
            )

        interpretacion_nueva = IntentDetectorService.detectar_intencion(mensaje)

        interpretacion_final = ChatbotAgendarService._merge_interpretaciones_agendamiento(
            interpretacion_directa,
            interpretacion_nueva,
        )

        return ChatbotAgendarService.preparar_agendamiento(
            user=user,
            veterinaria_id=veterinaria_id,
            interpretacion=interpretacion_final,
        )

    @staticmethod
    def continuar_seleccion_servicio(*, user, veterinaria_id, mensaje, contexto):
        opcion = ChatbotSelectionResolverService.resolver_opcion_por_mensaje(
            mensaje=mensaje,
            opciones=contexto.get("opciones", []),
        )

        if not opcion:
            return ChatbotSelectionResolverService.respuesta_no_entendida(
                contexto=contexto
            )

        data = contexto.get("data", {}) or {}
        interpretacion = data.get("interpretacion", {}) or {}
        id_mascota = data.get("id_mascota")
        id_servicio = opcion.get("id_servicio")

        mascota = ChatbotMascotaSelector.obtener_mascota_usuario_por_id(
            user=user,
            veterinaria_id=veterinaria_id,
            id_mascota=id_mascota,
        )

        if not mascota:
            return ChatbotResponseBuilder.error(
                code="MASCOTA_NO_ENCONTRADA",
                respuesta=(
                    "No pude recuperar la mascota seleccionada. "
                    "Intenta iniciar el agendamiento nuevamente."
                ),
            )

        servicio = ChatbotServicioSelector.obtener_servicio_activo_por_id(
            veterinaria_id=veterinaria_id,
            id_servicio=id_servicio,
        )

        if not servicio:
            return ChatbotResponseBuilder.error(
                code="SERVICIO_NO_ENCONTRADO",
                respuesta=(
                    "No pude recuperar el servicio seleccionado. "
                    "Intenta seleccionar otro servicio."
                ),
                contexto=contexto,
            )

        return ChatbotAgendarService._resolver_precio_y_payload(
            user=user,
            veterinaria_id=veterinaria_id,
            interpretacion=interpretacion,
            mascota=mascota,
            servicio=servicio,
        )

    @staticmethod
    def continuar_seleccion_horario(*, user, veterinaria_id, mensaje, contexto):
        opcion = ChatbotSelectionResolverService.resolver_opcion_por_mensaje(
            mensaje=mensaje,
            opciones=contexto.get("opciones", []),
        )

        if not opcion:
            return ChatbotSelectionResolverService.respuesta_no_entendida(
                contexto=contexto
            )

        data = contexto.get("data", {}) or {}
        payload = data.get("payload_crear_cita", {}) or {}

        if not payload:
            return ChatbotResponseBuilder.error(
                code="PAYLOAD_CITA_NO_ENCONTRADO",
                respuesta="No pude recuperar los datos de la cita. Intenta iniciar nuevamente.",
            )

        nueva_hora = opcion.get("hora_inicio")
        payload["hora_inicio"] = nueva_hora

        interpretacion = data.get("interpretacion", {}) or {}
        datos = interpretacion.get("datos", {}) or {}
        datos["hora_inicio"] = nueva_hora[:5]
        interpretacion["datos"] = datos

        data["interpretacion"] = interpretacion
        data["payload_crear_cita"] = payload

        mascota = data.get("mascota", {}) or {}
        servicio = data.get("servicio", {}) or {}
        precio = data.get("precio", {}) or {}
        direccion_cita = payload.get("direccion_cita")

        linea_direccion = ""
        if str(payload.get("modalidad") or "").strip().upper() == "DOMICILIO":
            linea_direccion = f"Dirección: {direccion_cita}\n"

        return ChatbotResponseBuilder.needs_confirmation(
            estado="ESPERANDO_CONFIRMACION_CREAR_CITA",
            respuesta=(
                f"Perfecto, actualicé el horario de la cita:\n"
                f"Mascota: {mascota.get('nombre')}\n"
                f"Servicio: {servicio.get('nombre')}\n"
                f"Fecha: {payload.get('fecha_programada')}\n"
                f"Hora: {payload.get('hora_inicio')}\n"
                f"Modalidad: {payload.get('modalidad')}\n"
                f"{linea_direccion}"
                f"Precio: {precio.get('precio')} Bs\n\n"
                "¿Confirmas que deseas agendar esta cita? Responde sí o no."
            ),
            data=data,
        )

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
            "agendar",
            "agenda",
            "crear cita",
            "reservar",
        ]

        return any(TextMatcher.normalize(palabra) in texto for palabra in afirmaciones)

    @staticmethod
    def _usuario_cancela_confirmacion(mensaje):
        texto = TextMatcher.normalize(mensaje)

        negaciones = [
            "no",
            "cancelar",
            "cancela",
            "mejor no",
            "no quiero",
            "anular",
        ]

        return any(TextMatcher.normalize(palabra) in texto for palabra in negaciones)

    @staticmethod
    def continuar_confirmacion_crear_cita(*, user, veterinaria_id, mensaje, contexto):
        if ChatbotAgendarService._usuario_cancela_confirmacion(mensaje):
            return ChatbotResponseBuilder.success(
                accion="AGENDAMIENTO_CANCELADO_POR_USUARIO",
                respuesta="De acuerdo, no agendé la cita.",
                data={},
                contexto=None,
            )

        if not ChatbotAgendarService._usuario_confirma(mensaje):
            return ChatbotResponseBuilder.needs_confirmation(
                estado="ESPERANDO_CONFIRMACION_CREAR_CITA",
                respuesta=(
                    "No pude identificar tu confirmación. "
                    "Escribe 'sí' para agendar o 'no' para cancelar."
                ),
                data=contexto.get("data", {}),
            )

        data = contexto.get("data", {}) or {}
        payload = data.get("payload_crear_cita", {}) or {}

        if not payload:
            return ChatbotResponseBuilder.error(
                code="PAYLOAD_CITA_NO_ENCONTRADO",
                respuesta=(
                    "No pude recuperar los datos de la cita. "
                    "Intenta iniciar el agendamiento nuevamente."
                ),
            )

        fecha_programada = ChatbotTimeUtils.to_date(payload.get("fecha_programada"))
        hora_inicio = ChatbotTimeUtils.to_time(payload.get("hora_inicio"))

        id_mascota = payload.get("mascota")
        id_servicio = payload.get("servicio")
        id_precio = payload.get("precio_servicio")
        modalidad = str(payload.get("modalidad") or "").strip().upper()
        direccion_cita = ChatbotAgendarService._normalizar_direccion(
            payload.get("direccion_cita")
        )
        descripcion = payload.get("descripcion")

        if modalidad == "CLINICA":
            direccion_cita = None

        if modalidad == "DOMICILIO" and not direccion_cita:
            return ChatbotResponseBuilder.needs_data(
                estado="ESPERANDO_DATOS_AGENDAMIENTO",
                respuesta="¿A qué dirección debemos acudir para la cita a domicilio?",
                faltan=["direccion_cita"],
                data=data,
            )

        if not fecha_programada or not hora_inicio:
            return ChatbotResponseBuilder.error(
                code="FECHA_HORA_INVALIDA",
                respuesta="La fecha u hora de la cita no tiene un formato válido.",
                data={"payload": payload},
            )

        # Validación de seguridad:
        # No confiamos ciegamente en los IDs que vuelven desde el frontend.
        mascota = ChatbotMascotaSelector.obtener_mascota_usuario_por_id(
            user=user,
            veterinaria_id=veterinaria_id,
            id_mascota=id_mascota,
        )

        if not mascota:
            return ChatbotResponseBuilder.error(
                code="MASCOTA_NO_VALIDA",
                respuesta=(
                    "No pude validar que la mascota seleccionada pertenezca a tu cuenta. "
                    "Intenta iniciar el agendamiento nuevamente."
                ),
            )

        servicio = ChatbotServicioSelector.obtener_servicio_activo_por_id(
            veterinaria_id=veterinaria_id,
            id_servicio=id_servicio,
        )

        if not servicio:
            return ChatbotResponseBuilder.error(
                code="SERVICIO_NO_VALIDO",
                respuesta=(
                    "No pude validar el servicio seleccionado. "
                    "Intenta iniciar el agendamiento nuevamente."
                ),
            )

        if modalidad == "DOMICILIO" and not servicio.disponible_domicilio:
            return ChatbotResponseBuilder.error(
                code="SERVICIO_NO_DISPONIBLE_DOMICILIO",
                respuesta=(
                    f"El servicio '{servicio.nombre}' no está disponible a domicilio. "
                    "Intenta iniciar el agendamiento nuevamente."
                ),
            )

        precios_validos = ChatbotPrecioSelector.listar_por_servicio_y_modalidad(
            veterinaria_id=veterinaria_id,
            servicio_id=servicio.id_servicio,
            modalidad=modalidad,
        )

        precio = None
        for precio_item in precios_validos:
            if getattr(precio_item, "id_precio", None) == id_precio:
                precio = precio_item
                break

        if not precio:
            return ChatbotResponseBuilder.error(
                code="PRECIO_NO_VALIDO",
                respuesta=(
                    "No pude validar el precio del servicio seleccionado. "
                    "Intenta iniciar el agendamiento nuevamente."
                ),
            )

        duracion = ChatbotAgendarService._obtener_duracion_valida(servicio)

        if not duracion:
            return ChatbotResponseBuilder.error(
                code="DURACION_SERVICIO_INVALIDA",
                respuesta=(
                    f"El servicio '{servicio.nombre}' no tiene una duración válida configurada. "
                    "No puedo agendarlo automáticamente."
                ),
            )

        inicio_dt = datetime.combine(fecha_programada, hora_inicio)
        hora_fin = (
            inicio_dt + timedelta(minutes=duracion)
        ).time()

        fecha_hora_programada = timezone.make_aware(
            inicio_dt,
            timezone.get_current_timezone(),
        )

        if fecha_hora_programada <= timezone.localtime():
            return ChatbotResponseBuilder.error(
                code="FECHA_HORA_PASADA",
                respuesta="No puedo agendar una cita en una fecha u hora pasada.",
            )

        try:
            cita = CitaService.crear_cita(
                veterinaria_id=veterinaria_id,
                usuario_id=user.id_usuario,
                mascota_id=getattr(mascota, "id_mascota", id_mascota),
                servicio_id=servicio.id_servicio,
                precio_servicio_id=precio.id_precio,
                fecha_programada=fecha_programada,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                modalidad=modalidad,
                direccion_cita=direccion_cita,
                descripcion=descripcion,
            )
        except Exception as exc:
            error_text = str(exc)

            if (
                "CONFLICTO_HORARIO" in error_text
                or "horario seleccionado ya esta ocupado" in error_text
                or "horario seleccionado ya está ocupado" in error_text
            ):
                return ChatbotAgendarService._responder_conflicto_con_horarios(
                    veterinaria_id=veterinaria_id,
                    fecha_programada=fecha_programada,
                    modalidad=modalidad,
                    servicio=servicio,
                    data=data,
                )

            return ChatbotResponseBuilder.error(
                code="ERROR_CREAR_CITA",
                respuesta="No pude crear la cita por un error inesperado.",
                data={"error": error_text},
            )

        return ChatbotResponseBuilder.success(
            accion="CITA_CREADA",
            respuesta=(
                f"Listo, tu cita fue agendada correctamente para "
                f"{cita.fecha_programada} a las {cita.hora_inicio.strftime('%H:%M')}."
            ),
            data={
                "cita": CitaSerializer(cita).data,
            },
            contexto=None,
        )
