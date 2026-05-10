from .chatbot_response_builder import ChatbotResponseBuilder

from ..selectors.chatbot_mascota_selector import ChatbotMascotaSelector
from ..selectors.chatbot_servicio_selector import ChatbotServicioSelector

from ...models.precioservicio import PrecioServicio


class ChatbotInfoService:
    @staticmethod
    def responder_servicios(*, veterinaria_id, contexto):
        servicios = ChatbotServicioSelector.listar_servicios_activos(
            veterinaria_id=veterinaria_id
        )

        precios = list(
            PrecioServicio.objects.select_related("servicio")
            .filter(
                veterinaria_id=veterinaria_id,
                estado=True,
                servicio__estado=True,
            )
            .order_by("servicio__nombre", "modalidad", "precio", "id_precio")
        )

        precios_por_servicio = {}
        for precio in precios:
            precios_por_servicio.setdefault(precio.servicio_id, []).append(precio)

        lineas = ["Estos son los servicios disponibles:"]
        servicios_data = []
        contador = 1

        for servicio in servicios:
            precios_servicio = precios_por_servicio.get(servicio.id_servicio, [])

            if not precios_servicio:
                lineas.append(
                    f"{contador}. {servicio.nombre} - precio no configurado"
                )
                contador += 1

            precios_data = []
            for precio in precios_servicio:
                modalidad = str(precio.modalidad or "").strip().upper() or "SIN_MODALIDAD"
                valor = f"{precio.precio} Bs"
                lineas.append(f"{contador}. {servicio.nombre} - {modalidad} - {valor}")
                contador += 1
                precios_data.append(
                    {
                        "id_precio": precio.id_precio,
                        "modalidad": modalidad,
                        "precio": str(precio.precio),
                        "descripcion": precio.descripcion,
                    }
                )

            servicios_data.append(
                {
                    "id_servicio": servicio.id_servicio,
                    "nombre": servicio.nombre,
                    "descripcion": servicio.descripcion,
                    "disponible_domicilio": servicio.disponible_domicilio,
                    "precios": precios_data,
                }
            )

        if not servicios:
            lineas = ["No hay servicios activos disponibles en este momento."]

        return ChatbotResponseBuilder.success(
            accion="INFO_SERVICIOS",
            respuesta="\n".join(lineas),
            data={
                "servicios": servicios_data,
            },
            contexto=contexto,
        )

    @staticmethod
    def responder_mascotas(*, user, veterinaria_id, contexto):
        mascotas = ChatbotMascotaSelector.listar_mascotas_usuario(
            user=user,
            veterinaria_id=veterinaria_id,
        )

        if not mascotas:
            return ChatbotResponseBuilder.success(
                accion="INFO_MASCOTAS",
                respuesta="No tienes mascotas registradas en esta veterinaria.",
                data={"mascotas": []},
                contexto=contexto,
            )

        lineas = ["Tus mascotas registradas son:"]
        mascotas_data = []

        for idx, mascota in enumerate(mascotas, start=1):
            nombre = getattr(mascota, "nombre", "Mascota")
            especie = ChatbotInfoService._obtener_especie_mascota(mascota)
            lineas.append(f"{idx}. {nombre} - {especie}")
            mascotas_data.append(
                {
                    "id_mascota": getattr(mascota, "id_mascota", None),
                    "nombre": nombre,
                    "especie": especie,
                }
            )

        return ChatbotResponseBuilder.success(
            accion="INFO_MASCOTAS",
            respuesta="\n".join(lineas),
            data={"mascotas": mascotas_data},
            contexto=contexto,
        )

    @staticmethod
    def responder_precios(*, veterinaria_id, mensaje, contexto):
        servicios_match = ChatbotServicioSelector.buscar_por_nombre(
            veterinaria_id=veterinaria_id,
            nombre=mensaje,
        )

        if not servicios_match:
            return ChatbotResponseBuilder.success(
                accion="INFO_PRECIOS",
                respuesta=(
                    "No encontré un servicio relacionado con tu consulta de precio. "
                    "Puedes escribir por ejemplo: 'precio de baño'."
                ),
                data={"precios": []},
                contexto=contexto,
            )

        servicios = [match["item"] for match in servicios_match[:5]]
        lineas = ["Estos son los precios que encontré:"]
        precios_data = []
        contador = 1

        for servicio in servicios:
            precios = list(
                PrecioServicio.objects.filter(
                    veterinaria_id=veterinaria_id,
                    servicio_id=servicio.id_servicio,
                    estado=True,
                    servicio__estado=True,
                ).order_by("modalidad", "precio", "id_precio")
            )

            if not precios:
                lineas.append(f"{contador}. {servicio.nombre} - precio no configurado")
                contador += 1
                precios_data.append(
                    {
                        "id_servicio": servicio.id_servicio,
                        "servicio_nombre": servicio.nombre,
                        "modalidad": None,
                        "precio": None,
                    }
                )
                continue

            for precio in precios:
                modalidad = str(precio.modalidad or "").strip().upper() or "SIN_MODALIDAD"
                lineas.append(
                    f"{contador}. {servicio.nombre} - {modalidad} - {precio.precio} Bs"
                )
                contador += 1
                precios_data.append(
                    {
                        "id_precio": precio.id_precio,
                        "id_servicio": servicio.id_servicio,
                        "servicio_nombre": servicio.nombre,
                        "modalidad": modalidad,
                        "precio": str(precio.precio),
                    }
                )

        return ChatbotResponseBuilder.success(
            accion="INFO_PRECIOS",
            respuesta="\n".join(lineas),
            data={"precios": precios_data},
            contexto=contexto,
        )

    @staticmethod
    def responder_modalidades(*, contexto):
        return ChatbotResponseBuilder.success(
            accion="INFO_MODALIDADES",
            respuesta=(
                "Puedes elegir CLINICA o DOMICILIO. "
                "Ten en cuenta que no todos los servicios están disponibles a domicilio."
            ),
            data={},
            contexto=contexto,
        )

    @staticmethod
    def _obtener_especie_mascota(mascota):
        posibles_campos = ["especie", "tipo", "raza"]

        for campo in posibles_campos:
            valor = getattr(mascota, campo, None)
            if not valor:
                continue

            if isinstance(valor, str):
                if valor.strip():
                    return valor.strip()
            else:
                nombre = getattr(valor, "nombre", None)
                if nombre:
                    return str(nombre)

        return "Sin especie"
