import re
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError

from apps.GestionInventarioProveedores.models import Producto, PuntoInventario, StockPunto
from apps.GestionServiciosyReserva.bot.utils.text_matcher import TextMatcher
from apps.GestiondeVentasyPagos.models import DetalleCarritoTemporal
from apps.GestiondeVentasyPagos.services.carrito_service import CarritoService
from apps.NotificacionesySeguimiento.models import DetallePedido, Pedido

from .chatbot_response_builder import ChatbotResponseBuilder


class ChatbotTiendaService:
    MENU_STATE = "TIENDA_MENU"
    SELECCION_PRODUCTO_STATE = "TIENDA_SELECCION_PRODUCTO"
    CANTIDAD_PRODUCTO_STATE = "TIENDA_CANTIDAD_PRODUCTO"
    DATOS_PEDIDO_STATE = "TIENDA_DATOS_PEDIDO"
    CONFIRMACION_PEDIDO_STATE = "TIENDA_CONFIRMACION_PEDIDO"

    CATEGORY_MENU = {
        "1": "COMIDA_Y_ALIMENTOS",
        "2": "JUGUETES",
        "3": "ACCESORIOS",
        "4": "SALUD_Y_BIENESTAR",
        "5": "VER_CARRITO",
    }

    CATEGORY_KEYWORDS = {
        "COMIDA_Y_ALIMENTOS": [
            "comida",
            "alimento",
            "alimentos",
            "croquetas",
            "snack",
            "snacks",
        ],
        "JUGUETES": ["juguete", "pelota", "mordedor", "rascador"],
        "ACCESORIOS": ["accesorio", "correa", "cama", "plato", "arnes", "collar"],
        "SALUD_Y_BIENESTAR": [
            "salud",
            "bienestar",
            "antipulgas",
            "vitamina",
            "suplemento",
            "higiene",
            "medicina",
            "shampoo",
        ],
    }

    @staticmethod
    def _with_follow_up_options(respuesta, opciones):
        opciones_limpias = [str(opcion).strip() for opcion in opciones if str(opcion).strip()]
        if not opciones_limpias:
            return respuesta

        lineas = [respuesta.rstrip(), "", "Puedes responder por ejemplo:"]
        lineas.extend(f"- {opcion}" for opcion in opciones_limpias)
        return "\n".join(lineas)

    @classmethod
    def es_mensaje_tienda(cls, mensaje, contexto=None):
        estado = ((contexto or {}).get("estado") or "").strip().upper()
        if estado.startswith("TIENDA_"):
            return True

        texto = TextMatcher.normalize(mensaje)
        if not texto:
            return False

        claves = [
            "producto",
            "productos",
            "comprar",
            "compra",
            "tienda",
            "catalogo",
            "carrito",
            "pedido",
            "alimento",
            "comida",
            "juguete",
            "accesorio",
            "salud",
            "bienestar",
        ]
        return any(clave in texto for clave in claves)

    @classmethod
    def procesar_mensaje(cls, *, user, veterinaria_id, mensaje, contexto=None):
        contexto = contexto or {}
        estado = str(contexto.get("estado") or "").strip().upper()

        if estado == cls.MENU_STATE:
            return cls._continuar_menu(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == cls.SELECCION_PRODUCTO_STATE:
            return cls._continuar_seleccion_producto(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == cls.CANTIDAD_PRODUCTO_STATE:
            return cls._continuar_cantidad_producto(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == cls.DATOS_PEDIDO_STATE:
            return cls._continuar_datos_pedido(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        if estado == cls.CONFIRMACION_PEDIDO_STATE:
            return cls._continuar_confirmacion_pedido(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
            )

        return cls._manejar_intencion_general(
            user=user,
            veterinaria_id=veterinaria_id,
            mensaje=mensaje,
            contexto=contexto,
        )

    @classmethod
    def _manejar_intencion_general(cls, *, user, veterinaria_id, mensaje, contexto):
        texto = TextMatcher.normalize(mensaje)

        if cls._wants_cart(texto):
            return cls._mostrar_carrito(user=user, veterinaria_id=veterinaria_id, contexto=contexto)

        if cls._wants_checkout(texto):
            return cls._iniciar_pedido(user=user, veterinaria_id=veterinaria_id, contexto=contexto)

        if cls._wants_remove(texto):
            return cls._resolver_operacion_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
                operacion="ELIMINAR",
            )

        if cls._wants_update(texto):
            return cls._resolver_operacion_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
                operacion="ACTUALIZAR",
            )

        if cls._wants_add(texto):
            return cls._resolver_operacion_producto(
                user=user,
                veterinaria_id=veterinaria_id,
                mensaje=mensaje,
                contexto=contexto,
                operacion="AGREGAR",
            )

        if cls._wants_store_menu(texto):
            return cls._mostrar_menu_tienda(contexto=contexto)

        return cls._buscar_productos(
            user=user,
            veterinaria_id=veterinaria_id,
            consulta=mensaje,
            contexto=contexto,
            operacion="CONSULTAR",
        )

    @classmethod
    def _continuar_menu(cls, *, user, veterinaria_id, mensaje, contexto):
        texto = TextMatcher.normalize(mensaje)
        opcion = cls._extract_menu_option(texto)
        if opcion == "VER_CARRITO":
            return cls._mostrar_carrito(user=user, veterinaria_id=veterinaria_id, contexto=contexto)

        if opcion:
            return cls._buscar_productos(
                user=user,
                veterinaria_id=veterinaria_id,
                consulta=opcion,
                contexto=contexto,
                operacion="CONSULTAR",
            )

        if cls._wants_cart(texto):
            return cls._mostrar_carrito(user=user, veterinaria_id=veterinaria_id, contexto=contexto)

        return cls._manejar_intencion_general(
            user=user,
            veterinaria_id=veterinaria_id,
            mensaje=mensaje,
            contexto=contexto,
        )

    @classmethod
    def _continuar_seleccion_producto(cls, *, user, veterinaria_id, mensaje, contexto):
        data = (contexto or {}).get("data") or {}
        opciones = data.get("opciones") or []
        operacion = str(data.get("operacion") or "CONSULTAR").upper()
        cantidad = data.get("cantidad")
        texto = TextMatcher.normalize(mensaje)

        if cls._wants_cart(texto):
            return cls._mostrar_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        if cls._wants_store_menu(texto) or cls._wants_cancel_selection(texto):
            return cls._mostrar_menu_tienda(contexto={"estado": cls.MENU_STATE, "data": {}})

        seleccion = cls._extract_selection_number(mensaje)
        if seleccion is None:
            return ChatbotResponseBuilder.needs_selection(
                respuesta="Escribe el numero del producto que deseas seleccionar.",
                tipo="PRODUCTO_TIENDA",
                estado=cls.SELECCION_PRODUCTO_STATE,
                opciones=opciones,
                data=data,
            )

        elegida = next((op for op in opciones if op.get("numero") == seleccion), None)
        if not elegida:
            return ChatbotResponseBuilder.error(
                code="OPCION_INVALIDA_TIENDA",
                respuesta="No encontre ese numero dentro de las opciones mostradas.",
                data={"opciones": opciones},
                contexto=contexto,
            )

        if operacion == "CONSULTAR":
            return cls._responder_detalle_producto(
                veterinaria_id=veterinaria_id,
                producto_id=elegida.get("id_producto"),
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        if operacion == "AGREGAR":
            if not cantidad:
                return ChatbotResponseBuilder.needs_data(
                    respuesta=f"Indica cuantas unidades de {elegida.get('nombre')} deseas agregar.",
                    faltan=["cantidad"],
                    data={
                        "operacion": "AGREGAR",
                        "id_producto": elegida.get("id_producto"),
                        "nombre": elegida.get("nombre"),
                    },
                    estado=cls.CANTIDAD_PRODUCTO_STATE,
                )

            return cls._agregar_producto_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                producto_id=elegida.get("id_producto"),
                cantidad=cantidad,
            )

        if operacion in {"ELIMINAR", "ACTUALIZAR"}:
            return cls._resolver_operacion_detalle_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                detalle_id=elegida.get("id_detalle_carrito"),
                operacion=operacion,
                cantidad=cantidad,
                nombre=elegida.get("nombre"),
            )

        return cls._mostrar_menu_tienda(contexto=contexto)

    @classmethod
    def _continuar_cantidad_producto(cls, *, user, veterinaria_id, mensaje, contexto):
        data = (contexto or {}).get("data") or {}
        texto = TextMatcher.normalize(mensaje)

        if cls._wants_cart(texto):
            return cls._mostrar_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        if cls._wants_store_menu(texto) or cls._wants_cancel_selection(texto):
            return cls._mostrar_menu_tienda(contexto={"estado": cls.MENU_STATE, "data": {}})

        cantidad = cls._extract_quantity(mensaje)
        if cantidad is None or cantidad <= 0:
            return ChatbotResponseBuilder.needs_data(
                respuesta="Necesito una cantidad valida mayor a cero.",
                faltan=["cantidad"],
                data=data,
                estado=cls.CANTIDAD_PRODUCTO_STATE,
            )

        operacion = str(data.get("operacion") or "AGREGAR").upper()
        if operacion == "AGREGAR":
            return cls._agregar_producto_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                producto_id=data.get("id_producto"),
                cantidad=cantidad,
            )

        if operacion == "ACTUALIZAR":
            return cls._resolver_operacion_detalle_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                detalle_id=data.get("id_detalle_carrito"),
                operacion="ACTUALIZAR",
                cantidad=cantidad,
                nombre=data.get("nombre"),
            )

        return cls._mostrar_menu_tienda(contexto=contexto)

    @classmethod
    def _continuar_datos_pedido(cls, *, user, veterinaria_id, mensaje, contexto):
        data = dict((contexto or {}).get("data") or {})
        texto = TextMatcher.normalize(mensaje)
        tipo_entrega = data.get("tipo_entrega")
        direccion_compartida = (contexto or {}).get("direccion_cita_compartida")

        if not tipo_entrega:
            tipo_entrega = cls._extract_delivery_type(texto)
            if not tipo_entrega:
                return ChatbotResponseBuilder.needs_data(
                    respuesta="Como quieres recibir tu pedido? Responde 1 para domicilio o 2 para recojo.",
                    faltan=["tipo_entrega"],
                    data=data,
                    estado=cls.DATOS_PEDIDO_STATE,
                )
            data["tipo_entrega"] = tipo_entrega

        if tipo_entrega == "DOMICILIO":
            direccion = (data.get("direccion_entrega") or "").strip()
            if not direccion:
                direccion = (direccion_compartida or "").strip()
            if not direccion:
                direccion = mensaje.strip() if not cls._extract_delivery_type(texto) else ""

            if not direccion:
                return ChatbotResponseBuilder.needs_data(
                    respuesta=(
                        "Comparte tu direccion de entrega o usa el boton de ubicacion "
                        "para continuar con el pedido."
                    ),
                    faltan=["direccion_entrega"],
                    data=data,
                    estado=cls.DATOS_PEDIDO_STATE,
                )

            data["direccion_entrega"] = direccion

        return cls._pedir_confirmacion_pedido(
            user=user,
            veterinaria_id=veterinaria_id,
            data=data,
        )

    @classmethod
    def _continuar_confirmacion_pedido(cls, *, user, veterinaria_id, mensaje, contexto):
        texto = TextMatcher.normalize(mensaje)
        if texto in {"no", "cancelar", "anular"}:
            return ChatbotResponseBuilder.success(
                accion="PEDIDO_CANCELADO_TIENDA",
                respuesta="Perfecto, no genere el pedido. Si deseas continuar luego, dime 'finalizar compra'.",
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        if texto not in {"si", "sí", "confirmar", "ok", "acepto"}:
            return ChatbotResponseBuilder.needs_confirmation(
                respuesta="Responde 'si' para confirmar el pedido o 'no' para cancelarlo.",
                estado=cls.CONFIRMACION_PEDIDO_STATE,
                data=(contexto or {}).get("data") or {},
            )

        data = (contexto or {}).get("data") or {}
        try:
            pedido = cls._crear_o_actualizar_pedido_desde_carrito(
                user=user,
                tenant_id=veterinaria_id,
                tipo_entrega=data.get("tipo_entrega"),
                direccion_entrega=data.get("direccion_entrega"),
                observacion="Pedido generado desde el chatbot.",
            )
        except ValidationError as error:
            return ChatbotResponseBuilder.error(
                code="ERROR_PEDIDO_TIENDA",
                respuesta=cls._extract_error_message(error),
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )
        except Exception:
            return ChatbotResponseBuilder.error(
                code="ERROR_PEDIDO_TIENDA",
                respuesta=(
                    "Ocurrio un error inesperado al generar el pedido. "
                    "Intenta nuevamente en unos segundos."
                ),
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        return ChatbotResponseBuilder.success(
            accion="PEDIDO_CREADO_TIENDA",
            respuesta=cls._with_follow_up_options(
                (
                f"Tu pedido #{pedido.id_pedido} fue generado correctamente por el chatbot. "
                "Te llevare directamente a la pantalla de pago para completar la compra."
                ),
                [
                    "'pagar ahora'",
                    "'ver mi carrito'",
                    "'seguir comprando'",
                ],
            ),
            data={
                "id_pedido": pedido.id_pedido,
                "tipo_entrega": pedido.tipo_entrega,
                "direccion_entrega": pedido.direccion_entrega,
                "total": str(pedido.total),
                "estado_pedido": pedido.estado_pedido,
            },
            contexto={"estado": cls.MENU_STATE, "data": {}},
        )

    @classmethod
    def _resolver_operacion_producto(cls, *, user, veterinaria_id, mensaje, contexto, operacion):
        cantidad = cls._extract_quantity(mensaje)
        consulta = cls._clean_product_query(mensaje)
        return cls._buscar_productos(
            user=user,
            veterinaria_id=veterinaria_id,
            consulta=consulta or mensaje,
            contexto=contexto,
            operacion=operacion,
            cantidad=cantidad,
        )

    @classmethod
    def _resolver_operacion_carrito(cls, *, user, veterinaria_id, mensaje, contexto, operacion):
        carrito = CarritoService.obtener_carrito(user=user, tenant_id=veterinaria_id)
        detalles = [detalle for detalle in carrito.detalles.all() if detalle.estado]
        if not detalles:
            return ChatbotResponseBuilder.error(
                code="CARRITO_VACIO",
                respuesta="Tu carrito esta vacio en este momento.",
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        cantidad = cls._extract_quantity(mensaje) if operacion == "ACTUALIZAR" else None
        consulta = cls._clean_product_query(mensaje)
        matches = TextMatcher.find_best_matches(
            consulta or mensaje,
            detalles,
            label_getter=lambda item: getattr(item.producto, "nombre", item.descripcion_item or ""),
            min_score=0.35,
        )

        if not matches:
            return ChatbotResponseBuilder.error(
                code="PRODUCTO_CARRITO_NO_ENCONTRADO",
                respuesta="No encontre ese producto dentro de tu carrito.",
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        if len(matches) == 1:
            detalle = matches[0]["item"]
            return cls._resolver_operacion_detalle_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                detalle_id=detalle.id_detalle_carrito,
                operacion=operacion,
                cantidad=cantidad,
                nombre=getattr(detalle.producto, "nombre", detalle.descripcion_item),
            )

        opciones = [
            {
                "numero": idx,
                "id_detalle_carrito": match["item"].id_detalle_carrito,
                "nombre": getattr(match["item"].producto, "nombre", match["item"].descripcion_item),
            }
            for idx, match in enumerate(matches[:5], start=1)
        ]

        lineas = ["Encontre varios productos en tu carrito:"]
        for opcion in opciones:
            lineas.append(f"{opcion['numero']}. {opcion['nombre']}")
        lineas.append("\nEscribe el numero del producto que deseas gestionar.")

        return ChatbotResponseBuilder.needs_selection(
            respuesta=cls._with_follow_up_options(
                "\n".join(lineas),
                [
                    "'1'",
                    "'2'",
                    "'ver mi carrito'",
                ],
            ),
            tipo="DETALLE_CARRITO_TIENDA",
            estado=cls.SELECCION_PRODUCTO_STATE,
            opciones=opciones,
            data={
                "operacion": operacion,
                "cantidad": cantidad,
                "opciones": opciones,
            },
        )

    @classmethod
    def _resolver_operacion_detalle_carrito(cls, *, user, veterinaria_id, detalle_id, operacion, cantidad, nombre):
        if operacion == "ELIMINAR":
            try:
                carrito = CarritoService.eliminar_item(
                    user=user,
                    tenant_id=veterinaria_id,
                    detalle_id=detalle_id,
                )
            except ValidationError as error:
                return ChatbotResponseBuilder.error(
                    code="ERROR_CARRITO_TIENDA",
                    respuesta=cls._extract_error_message(error),
                    contexto={"estado": cls.MENU_STATE, "data": {}},
                )
            return cls._respuesta_carrito_actualizado(
                carrito=carrito,
                respuesta=f"Quite {nombre} de tu carrito.",
            )

        if cantidad is None or cantidad <= 0:
            return ChatbotResponseBuilder.needs_data(
                respuesta=f"Indica la nueva cantidad para {nombre}.",
                faltan=["cantidad"],
                data={
                    "operacion": "ACTUALIZAR",
                    "id_detalle_carrito": detalle_id,
                    "nombre": nombre,
                },
                estado=cls.CANTIDAD_PRODUCTO_STATE,
            )

        try:
            carrito = CarritoService.actualizar_cantidad(
                user=user,
                tenant_id=veterinaria_id,
                detalle_id=detalle_id,
                cantidad=Decimal(str(cantidad)),
            )
        except ValidationError as error:
            return ChatbotResponseBuilder.error(
                code="ERROR_CARRITO_TIENDA",
                respuesta=cls._extract_error_message(error),
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )
        return cls._respuesta_carrito_actualizado(
            carrito=carrito,
            respuesta=f"Actualice {nombre} a {cantidad} unidad(es) en tu carrito.",
        )

    @classmethod
    def _buscar_productos(cls, *, user, veterinaria_id, consulta, contexto, operacion, cantidad=None):
        productos = cls._match_products(veterinaria_id=veterinaria_id, consulta=consulta)

        if not productos:
            return ChatbotResponseBuilder.error(
                code="PRODUCTO_NO_ENCONTRADO",
                respuesta=(
                    "No encontre productos relacionados con tu consulta. "
                    "Prueba con algo como 'alimento para gato', 'juguetes' o 'ver carrito'."
                ),
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        if len(productos) == 1 and operacion == "CONSULTAR":
            return cls._responder_detalle_producto(
                veterinaria_id=veterinaria_id,
                producto_id=productos[0].id_producto,
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        if len(productos) == 1 and operacion == "AGREGAR" and cantidad:
            return cls._agregar_producto_carrito(
                user=user,
                veterinaria_id=veterinaria_id,
                producto_id=productos[0].id_producto,
                cantidad=cantidad,
            )

        opciones = []
        lineas = ["Estos son los productos que encontre:"]
        for idx, producto in enumerate(productos[:5], start=1):
            stock = cls._stock_disponible(veterinaria_id=veterinaria_id, producto_id=producto.id_producto)
            precio = cls._resolve_display_price(producto)
            opciones.append(
                {
                    "numero": idx,
                    "id_producto": producto.id_producto,
                    "nombre": producto.nombre,
                }
            )
            lineas.append(
                f"{idx}. {producto.nombre} - Bs {precio} - stock disponible: {stock}"
            )
        lineas.append("\nEscribe el numero del producto para ver detalle o continuar.")

        return ChatbotResponseBuilder.needs_selection(
            respuesta=cls._with_follow_up_options(
                "\n".join(lineas),
                [
                    "'1'",
                    "'2'",
                    "'ver mi carrito'",
                ],
            ),
            tipo="PRODUCTO_TIENDA",
            estado=cls.SELECCION_PRODUCTO_STATE,
            opciones=opciones,
            data={
                "operacion": operacion,
                "cantidad": cantidad,
                "opciones": opciones,
            },
        )

    @classmethod
    def _responder_detalle_producto(cls, *, veterinaria_id, producto_id, contexto):
        producto = cls._base_product_queryset(veterinaria_id=veterinaria_id).filter(id_producto=producto_id).first()
        if not producto:
            return ChatbotResponseBuilder.error(
                code="PRODUCTO_NO_ENCONTRADO",
                respuesta="No pude recuperar el detalle de ese producto.",
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        stock = cls._stock_disponible(veterinaria_id=veterinaria_id, producto_id=producto.id_producto)
        relacionados = cls._related_products(veterinaria_id=veterinaria_id, producto=producto)
        precio = cls._resolve_display_price(producto)
        descripcion = (producto.descripcion or "Sin descripcion disponible.").strip()

        lineas = [
            f"{producto.nombre}",
            f"Descripcion: {descripcion}",
            f"Precio: Bs {precio}",
            f"Disponibilidad: {'Disponible' if stock > 0 else 'Sin stock'}",
            f"Stock referencial: {stock}",
            f"Categoria: {getattr(getattr(producto, 'categoria_producto', None), 'nombre', 'Sin categoria')}",
        ]
        if getattr(producto, "imagen", None):
            lineas.append("Imagen: disponible en la ficha del producto.")
        if relacionados:
            lineas.append("")
            lineas.append("Productos relacionados:")
            for idx, relacionado in enumerate(relacionados, start=1):
                lineas.append(f"{idx}. {relacionado['nombre']} - Bs {relacionado['precio']}")
        lineas.append("")
        lineas.append(
            "Si deseas agregarlo al carrito, escribeme por ejemplo: "
            f"'agrega 1 {producto.nombre}'."
        )

        return ChatbotResponseBuilder.success(
            accion="DETALLE_PRODUCTO_TIENDA",
            respuesta=cls._with_follow_up_options(
                "\n".join(lineas),
                [
                    f"'agrega 1 {producto.nombre}'",
                    "'ver mi carrito'",
                    "'buscar otro producto'",
                ],
            ),
            data={
                "producto": {
                    "id_producto": producto.id_producto,
                    "nombre": producto.nombre,
                    "descripcion": producto.descripcion,
                    "precio": str(precio),
                    "stock_disponible": str(stock),
                    "imagen_url": getattr(getattr(producto, "imagen", None), "url", None),
                    "categoria": getattr(getattr(producto, "categoria_producto", None), "nombre", None),
                    "relacionados": relacionados,
                }
            },
            contexto=contexto,
        )

    @classmethod
    def _agregar_producto_carrito(cls, *, user, veterinaria_id, producto_id, cantidad):
        try:
            carrito = CarritoService.agregar_item(
                user=user,
                tenant_id=veterinaria_id,
                data={
                    "tipo_item": DetalleCarritoTemporal.TipoItem.PRODUCTO,
                    "producto": Producto.objects.filter(
                        id_producto=producto_id,
                        veterinaria_id=veterinaria_id,
                    ).first(),
                    "cantidad": Decimal(str(cantidad)),
                },
            )
        except ValidationError as error:
            return ChatbotResponseBuilder.error(
                code="ERROR_CARRITO_TIENDA",
                respuesta=cls._extract_error_message(error),
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        producto = Producto.objects.filter(id_producto=producto_id).first()
        return cls._respuesta_carrito_actualizado(
            carrito=carrito,
            respuesta=f"Agregue {cantidad} unidad(es) de {getattr(producto, 'nombre', 'ese producto')} a tu carrito.",
        )

    @classmethod
    def _mostrar_carrito(cls, *, user, veterinaria_id, contexto):
        carrito = CarritoService.obtener_carrito(user=user, tenant_id=veterinaria_id)
        detalles = [detalle for detalle in carrito.detalles.all() if detalle.estado]
        if not detalles:
            return ChatbotResponseBuilder.success(
                accion="VER_CARRITO_TIENDA",
                respuesta="Tu carrito esta vacio. Puedes buscar productos por categoria o por nombre.",
                data={"items": [], "total_estimado": str(carrito.total_estimado)},
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        lineas = ["Este es el resumen de tu carrito:"]
        items = []
        for idx, detalle in enumerate(detalles, start=1):
            nombre = getattr(detalle.producto, "nombre", detalle.descripcion_item or "Producto")
            lineas.append(
                f"{idx}. {nombre} - cant. {detalle.cantidad} - subtotal Bs {detalle.subtotal_estimado}"
            )
            items.append(
                {
                    "id_detalle_carrito": detalle.id_detalle_carrito,
                    "producto": detalle.producto_id,
                    "nombre": nombre,
                    "cantidad": str(detalle.cantidad),
                    "subtotal": str(detalle.subtotal_estimado),
                }
            )
        lineas.append(f"\nTotal estimado: Bs {carrito.total_estimado}")
        lineas.append(
            "Puedes escribirme 'actualiza cantidad de ...', 'quita ...' o 'finalizar compra'."
        )

        return ChatbotResponseBuilder.success(
            accion="VER_CARRITO_TIENDA",
            respuesta=cls._with_follow_up_options(
                "\n".join(lineas),
                [
                    "'finalizar compra'",
                    "'actualiza cantidad de ...'",
                    "'quita ...'",
                ],
            ),
            data={
                "items": items,
                "subtotal_estimado": str(carrito.subtotal_estimado),
                "total_estimado": str(carrito.total_estimado),
            },
            contexto={"estado": cls.MENU_STATE, "data": {}},
        )

    @classmethod
    def _iniciar_pedido(cls, *, user, veterinaria_id, contexto):
        carrito = CarritoService.obtener_carrito(user=user, tenant_id=veterinaria_id)
        detalles = [detalle for detalle in carrito.detalles.all() if detalle.estado]
        if not detalles:
            return ChatbotResponseBuilder.error(
                code="CARRITO_VACIO",
                respuesta="No puedo generar el pedido porque tu carrito esta vacio.",
                contexto={"estado": cls.MENU_STATE, "data": {}},
            )

        lineas = ["Antes de confirmar tu compra, este es tu resumen:"]
        for idx, detalle in enumerate(detalles, start=1):
            nombre = getattr(detalle.producto, "nombre", detalle.descripcion_item or "Producto")
            lineas.append(
                f"{idx}. {nombre} - cant. {detalle.cantidad} - Bs {detalle.subtotal_estimado}"
            )
        lineas.append(f"\nTotal estimado: Bs {carrito.total_estimado}")
        lineas.append("Como quieres recibir tu pedido?")
        lineas.append("1. A domicilio")
        lineas.append("2. Recojo en veterinaria")

        return ChatbotResponseBuilder.needs_data(
            respuesta="\n".join(lineas),
            faltan=["tipo_entrega"],
            data={},
            estado=cls.DATOS_PEDIDO_STATE,
        )

    @classmethod
    def _pedir_confirmacion_pedido(cls, *, user, veterinaria_id, data):
        carrito = CarritoService.obtener_carrito(user=user, tenant_id=veterinaria_id)
        tipo_entrega = data.get("tipo_entrega")
        direccion = data.get("direccion_entrega")
        costo_envio = Decimal("10.00") if tipo_entrega == "DOMICILIO" else Decimal("0.00")
        total = Decimal(str(carrito.total_estimado or "0")) + costo_envio

        lineas = [
            "Este es el resumen final de tu pedido:",
            f"Subtotal productos: Bs {carrito.total_estimado}",
            f"Tipo de entrega: {tipo_entrega}",
            f"Costo de envio: Bs {costo_envio}",
            f"Total final: Bs {total}",
        ]
        if direccion:
            lineas.append(f"Direccion de entrega: {direccion}")
        lineas.append("")
        lineas.append("Responde 'si' para confirmar el pedido o 'no' para cancelarlo.")

        return ChatbotResponseBuilder.needs_confirmation(
            respuesta=cls._with_follow_up_options(
                "\n".join(lineas),
                [
                    "'si'",
                    "'no'",
                    "'ver mi carrito'",
                ],
            ),
            estado=cls.CONFIRMACION_PEDIDO_STATE,
            data=data,
        )

    @classmethod
    def _mostrar_menu_tienda(cls, *, contexto):
        respuesta = (
            "Hola. Bienvenido a la tienda PetHome.\n"
            "Que tipo de productos buscas?\n\n"
            "1. Comida y Alimentos\n"
            "2. Juguetes\n"
            "3. Accesorios\n"
            "4. Salud y Bienestar\n"
            "5. Ver mi carrito\n\n"
            "Tambien puedes escribirme algo como:\n"
            "- 'busca alimento para gato'\n"
            "- 'agrega 2 pelotas'\n"
            "- 'quita el shampoo'\n"
            "- 'finalizar compra'"
        )
        return ChatbotResponseBuilder.success(
            accion="MENU_TIENDA",
            respuesta=respuesta,
            contexto={"estado": cls.MENU_STATE, "data": {}},
        )

    @classmethod
    def _respuesta_carrito_actualizado(cls, *, carrito, respuesta):
        return ChatbotResponseBuilder.success(
            accion="CARRITO_ACTUALIZADO_TIENDA",
            respuesta=cls._with_follow_up_options(
                f"{respuesta}\nTotal estimado actual: Bs {carrito.total_estimado}",
                [
                    "'finalizar compra'",
                    "'ver mi carrito'",
                    "'buscar otro producto'",
                ],
            ),
            data={
                "subtotal_estimado": str(carrito.subtotal_estimado),
                "total_estimado": str(carrito.total_estimado),
            },
            contexto={"estado": cls.MENU_STATE, "data": {}},
        )

    @classmethod
    def _match_products(cls, *, veterinaria_id, consulta):
        query = TextMatcher.normalize(consulta)
        queryset = list(cls._base_product_queryset(veterinaria_id=veterinaria_id)[:80])

        category = cls._extract_menu_option(query) or cls._infer_category_from_query(query)
        if category and category != "VER_CARRITO":
            keywords = cls.CATEGORY_KEYWORDS.get(category, [])
            filtered = [
                producto
                for producto in queryset
                if any(
                    keyword in TextMatcher.normalize(
                        " ".join(
                            [
                                producto.nombre or "",
                                producto.descripcion or "",
                                getattr(getattr(producto, "categoria_producto", None), "nombre", "") or "",
                            ]
                        )
                    )
                    for keyword in keywords
                )
            ]
            if filtered:
                queryset = filtered

        if not query or category:
            return queryset[:5]

        matches = TextMatcher.find_best_matches(
            query,
            queryset,
            label_getter=lambda producto: " ".join(
                [
                    producto.nombre or "",
                    producto.descripcion or "",
                    getattr(getattr(producto, "categoria_producto", None), "nombre", "") or "",
                    producto.tipo_mascota or "",
                ]
            ),
            min_score=0.28,
        )
        return [match["item"] for match in matches[:5]]

    @classmethod
    def _related_products(cls, *, veterinaria_id, producto):
        relacionados = (
            cls._base_product_queryset(veterinaria_id=veterinaria_id)
            .filter(categoria_producto=producto.categoria_producto)
            .exclude(id_producto=producto.id_producto)[:3]
        )
        return [
            {
                "id_producto": item.id_producto,
                "nombre": item.nombre,
                "precio": str(cls._resolve_display_price(item)),
            }
            for item in relacionados
        ]

    @classmethod
    def _base_product_queryset(cls, *, veterinaria_id):
        return (
            Producto.objects.select_related("categoria_producto")
            .filter(
                veterinaria_id=veterinaria_id,
                estado=True,
                visible_catalogo=True,
            )
            .order_by("-destacado", "nombre")
        )

    @classmethod
    def _stock_disponible(cls, *, veterinaria_id, producto_id):
        return (
            StockPunto.objects.filter(
                veterinaria_id=veterinaria_id,
                producto_id=producto_id,
                numero_lote__isnull=True,
            ).aggregate(
                total=Coalesce(
                    Sum("cantidad"),
                    Decimal("0"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ).get("total")
            or Decimal("0")
        )

    @classmethod
    def _resolve_display_price(cls, producto):
        if (
            getattr(producto, "tiene_promocion", False)
            and getattr(producto, "precio_promocional", None)
            and producto.precio_promocional > 0
        ):
            return producto.precio_promocional
        return producto.precio_venta or Decimal("0")

    @classmethod
    def _extract_quantity(cls, mensaje):
        match = re.search(r"(\d+(?:[.,]\d+)?)", mensaje or "")
        if not match:
            return None
        value = match.group(1).replace(",", ".")
        try:
            return Decimal(value)
        except Exception:
            return None

    @classmethod
    def _extract_selection_number(cls, mensaje):
        texto = TextMatcher.normalize(mensaje)
        if texto.isdigit():
            return int(texto)
        match = re.search(r"\b(\d+)\b", texto)
        if match:
            return int(match.group(1))
        return None

    @classmethod
    def _extract_menu_option(cls, texto):
        if texto in cls.CATEGORY_KEYWORDS:
            return texto

        if texto in cls.CATEGORY_MENU:
            return cls.CATEGORY_MENU[texto]

        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            if any(keyword in texto for keyword in keywords):
                return category

        if "carrito" in texto:
            return "VER_CARRITO"
        return None

    @classmethod
    def _infer_category_from_query(cls, texto):
        return cls._extract_menu_option(texto)

    @classmethod
    def _extract_delivery_type(cls, texto):
        if texto in {"1", "domicilio"} or "domicilio" in texto or "envio" in texto:
            return "DOMICILIO"
        if texto in {"2", "recojo", "recoger"} or "recojo" in texto or "recoger" in texto:
            return "RECOJO"
        return None

    @classmethod
    def _clean_product_query(cls, mensaje):
        texto = TextMatcher.normalize(mensaje)
        patrones = [
            "quiero comprar",
            "comprar",
            "agrega",
            "anade",
            "añade",
            "quita",
            "elimina",
            "borra",
            "actualiza cantidad de",
            "actualiza",
            "cambia cantidad de",
            "cambia",
            "modifica cantidad de",
            "modifica",
            "del carrito",
            "carrito",
        ]
        for patron in patrones:
            texto = texto.replace(TextMatcher.normalize(patron), " ")
        texto = re.sub(r"\b\d+(?:[.,]\d+)?\b", " ", texto)
        return re.sub(r"\s+", " ", texto).strip()

    @staticmethod
    def _wants_store_menu(texto):
        claves = ["tienda", "catalogo", "catalogo de productos", "productos disponibles"]
        return any(clave in texto for clave in claves)

    @staticmethod
    def _wants_cancel_selection(texto):
        claves = ["ninguno", "ninguna", "cancelar", "volver", "atras", "atras por favor"]
        return texto in claves or any(clave == texto for clave in claves)

    @staticmethod
    def _wants_cart(texto):
        return "carrito" in texto or "ver mi carrito" in texto

    @staticmethod
    def _wants_checkout(texto):
        claves = ["finalizar compra", "confirmar pedido", "crear pedido", "hacer pedido", "terminar compra"]
        return any(clave in texto for clave in claves)

    @staticmethod
    def _wants_add(texto):
        claves = ["agrega", "anade", "añade", "suma", "quiero comprar", "llevar"]
        return any(clave in texto for clave in claves)

    @staticmethod
    def _wants_remove(texto):
        claves = ["quita", "elimina", "borra", "saca"]
        return any(clave in texto for clave in claves)

    @staticmethod
    def _wants_update(texto):
        claves = ["actualiza", "cambia", "modifica"]
        return any(clave in texto for clave in claves) and "cantidad" in texto

    @staticmethod
    def _extract_error_message(error):
        detail = getattr(error, "detail", None)
        if isinstance(detail, dict):
            values = []
            for value in detail.values():
                if isinstance(value, list):
                    values.extend(str(item) for item in value)
                else:
                    values.append(str(value))
            return " ".join(values)
        return str(error)

    @classmethod
    @transaction.atomic
    def _crear_o_actualizar_pedido_desde_carrito(
        cls,
        *,
        user,
        tenant_id,
        tipo_entrega,
        direccion_entrega=None,
        observacion="",
    ):
        carrito = CarritoService.obtener_carrito(user=user, tenant_id=tenant_id)
        detalles = [detalle for detalle in carrito.detalles.all() if detalle.estado]
        if not detalles:
            raise ValidationError({"detail": "El carrito esta vacio."})

        if tipo_entrega not in {"DOMICILIO", "RECOJO"}:
            raise ValidationError({"tipo_entrega": "Tipo de entrega no valido."})

        if tipo_entrega == "DOMICILIO" and not (direccion_entrega or "").strip():
            raise ValidationError({"direccion_entrega": "La direccion es obligatoria para pedidos a domicilio."})

        punto_almacen = PuntoInventario.objects.filter(
            veterinaria_id=tenant_id,
            estado=True,
            tipo=PuntoInventario.TipoPunto.ALMACEN_GENERAL,
        ).order_by("id_punto").first()
        if not punto_almacen:
            raise ValidationError({"detail": "No existe almacen principal configurado para despachar productos."})

        for detalle in detalles:
            if detalle.tipo_item != DetalleCarritoTemporal.TipoItem.PRODUCTO:
                continue
            stock = StockPunto.objects.filter(
                veterinaria_id=tenant_id,
                punto_inventario=punto_almacen,
                producto=detalle.producto,
                numero_lote__isnull=True,
            ).first()
            disponible = stock.cantidad if stock else Decimal("0")
            if disponible < detalle.cantidad:
                raise ValidationError(
                    {
                        "detail": (
                            f"Stock insuficiente para '{detalle.producto.nombre}'. "
                            f"Disponible: {disponible}, requerido: {detalle.cantidad}."
                        )
                    }
                )

        costo_envio = Decimal("10.00") if tipo_entrega == "DOMICILIO" else Decimal("0.00")
        subtotal = Decimal(str(carrito.total_estimado or "0"))
        total = subtotal + costo_envio

        pedido = Pedido.objects.filter(
            usuario=user,
            veterinaria_id=tenant_id,
            estado_pedido="PENDIENTE",
            estado=True,
        ).first()

        if pedido:
            pedido.detalles.all().delete()
            pedido.tipo_entrega = tipo_entrega
            pedido.direccion_entrega = direccion_entrega if tipo_entrega == "DOMICILIO" else None
            pedido.observacion = observacion
            pedido.subtotal = subtotal
            pedido.costo_envio = costo_envio
            pedido.total = total
            pedido.save()
        else:
            pedido = Pedido.objects.create(
                usuario=user,
                veterinaria_id=tenant_id,
                direccion_entrega=direccion_entrega if tipo_entrega == "DOMICILIO" else None,
                tipo_entrega=tipo_entrega,
                estado_pedido="PENDIENTE",
                subtotal=subtotal,
                costo_envio=costo_envio,
                total=total,
                observacion=observacion,
            )

        for detalle in detalles:
            if detalle.tipo_item != DetalleCarritoTemporal.TipoItem.PRODUCTO:
                continue
            DetallePedido.objects.create(
                pedido=pedido,
                producto=detalle.producto,
                cantidad=int(detalle.cantidad),
                precio_unitario=detalle.precio_unitario_estimado,
                subtotal=detalle.subtotal_estimado,
                observacion=detalle.observacion,
            )

        return pedido
