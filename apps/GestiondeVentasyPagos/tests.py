from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models import Rol, User, Veterinaria
from apps.GestionClientesyMascotas.models import Mascota
from apps.GestionInventarioProveedores.models import (
    CategoriaProducto,
    MovimientoInventario,
    Producto,
    PuntoInventario,
    StockPunto,
)
from apps.GestionServiciosyReserva.models import CategoriaServicio, Especie, PrecioServicio, Raza, Servicio, Cita
from apps.GestiondeVentasyPagos.models import Venta, Pago, TransaccionPago, ComprobantePago
from apps.NotificacionesySeguimiento.models import Pedido, Seguimiento
from apps.AutenticacionySeguridad.models import BillingDemoEvent
from django.utils import timezone
import json


class CarritoTemporalMobileTests(APITestCase):
    def setUp(self):
        self.vet_a = Veterinaria.objects.create(
            nombre="Vet Carrito A",
            slug="vet-carrito-a",
            correo="vet-carrito-a@example.com",
        )
        self.vet_b = Veterinaria.objects.create(
            nombre="Vet Carrito B",
            slug="vet-carrito-b",
            correo="vet-carrito-b@example.com",
        )

        self.rol_client = Rol.objects.create(nombre=RoleEnum.CLIENT.value, descripcion="Cliente")
        self.rol_admin = Rol.objects.create(nombre=RoleEnum.ADMIN.value, descripcion="Admin")

        self.client_a = User.objects.create(
            correo="cliente-a-carrito@example.com",
            role=self.rol_client,
            veterinaria=self.vet_a,
            is_active=True,
        )
        self.client_same_tenant_other = User.objects.create(
            correo="cliente-otro-carrito@example.com",
            role=self.rol_client,
            veterinaria=self.vet_a,
            is_active=True,
        )
        self.client_b = User.objects.create(
            correo="cliente-b-carrito@example.com",
            role=self.rol_client,
            veterinaria=self.vet_b,
            is_active=True,
        )
        self.admin_a = User.objects.create(
            correo="admin-a-carrito@example.com",
            role=self.rol_admin,
            veterinaria=self.vet_a,
            is_active=True,
            is_staff=True,
        )

        self.cat_producto_a = CategoriaProducto.objects.create(
            nombre="Alimentos A",
            veterinaria=self.vet_a,
            estado=True,
        )
        self.cat_producto_b = CategoriaProducto.objects.create(
            nombre="Alimentos B",
            veterinaria=self.vet_b,
            estado=True,
        )
        self.producto_a = Producto.objects.create(
            categoria_producto=self.cat_producto_a,
            nombre="Alimento premium A",
            precio_venta=Decimal("50.00"),
            visible_catalogo=True,
            estado=True,
            veterinaria=self.vet_a,
        )
        self.producto_b = Producto.objects.create(
            categoria_producto=self.cat_producto_b,
            nombre="Alimento premium B",
            precio_venta=Decimal("35.00"),
            visible_catalogo=True,
            estado=True,
            veterinaria=self.vet_b,
        )
        self.punto_a = PuntoInventario.objects.create(
            veterinaria=self.vet_a,
            tipo=PuntoInventario.TipoPunto.ALMACEN_GENERAL,
            nombre="Almacen Central A",
            estado=True,
        )
        StockPunto.objects.create(
            punto_inventario=self.punto_a,
            producto=self.producto_a,
            veterinaria=self.vet_a,
            cantidad=Decimal("10.00"),
            cantidad_minima=Decimal("1.00"),
        )

        self.cat_servicio_a = CategoriaServicio.objects.create(
            nombre="Higiene A",
            descripcion="Servicios higiene A",
            veterinaria=self.vet_a,
            estado=True,
        )
        self.cat_servicio_b = CategoriaServicio.objects.create(
            nombre="Higiene B",
            descripcion="Servicios higiene B",
            veterinaria=self.vet_b,
            estado=True,
        )
        self.servicio_a = Servicio.objects.create(
            nombre="Baño A",
            descripcion="Baño para mascotas A",
            categoria=self.cat_servicio_a,
            estado=True,
            veterinaria=self.vet_a,
        )
        self.servicio_b = Servicio.objects.create(
            nombre="Baño B",
            descripcion="Baño para mascotas B",
            categoria=self.cat_servicio_b,
            estado=True,
            veterinaria=self.vet_b,
        )
        self.precio_servicio_a = PrecioServicio.objects.create(
            servicio=self.servicio_a,
            variacion="General",
            modalidad="Clinica",
            precio=Decimal("80.00"),
            estado=True,
            veterinaria=self.vet_a,
        )
        self.precio_servicio_b = PrecioServicio.objects.create(
            servicio=self.servicio_b,
            variacion="General",
            modalidad="Clinica",
            precio=Decimal("90.00"),
            estado=True,
            veterinaria=self.vet_b,
        )

        self.especie = Especie.objects.create(nombre="Canino Carrito")
        self.raza = Raza.objects.create(nombre="Mestizo Carrito", especie=self.especie)
        self.mascota_a = Mascota.objects.create(
            usuario=self.client_a,
            especie=self.especie,
            raza=self.raza,
            veterinaria=self.vet_a,
            nombre="Firulais",
            fecha_nac=date(2023, 1, 1),
            estado=True,
        )
        self.mascota_otra_persona = Mascota.objects.create(
            usuario=self.client_same_tenant_other,
            especie=self.especie,
            raza=self.raza,
            veterinaria=self.vet_a,
            nombre="Luna",
            fecha_nac=date(2023, 2, 1),
            estado=True,
        )

    def test_cliente_obtiene_carrito_vacio(self):
        self.client.force_login(self.client_a)
        response = self.client.get("/api/gestion/ventas-pagos/carrito/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_carrito"], "ACTIVO")
        self.assertEqual(response.data["detalles"], [])
        self.assertEqual(Decimal(response.data["subtotal_estimado"]), Decimal("0"))
        self.assertEqual(Decimal(response.data["total_estimado"]), Decimal("0"))

    def test_agregar_producto_no_crea_venta_pedido_pago_ni_movimiento(self):
        self.client.force_login(self.client_a)
        ventas_antes = Venta.objects.count()
        pedidos_antes = Pedido.objects.count()
        movimientos_antes = MovimientoInventario.objects.count()
        stock_antes = StockPunto.objects.get(producto=self.producto_a, veterinaria=self.vet_a).cantidad

        response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto_a.id_producto,
                "cantidad": "2",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["detalles"]), 1)
        self.assertEqual(response.data["detalles"][0]["tipo_item"], "PRODUCTO")
        self.assertEqual(Decimal(response.data["total_estimado"]), Decimal("100.00"))

        self.assertEqual(Venta.objects.count(), ventas_antes)
        self.assertEqual(Pedido.objects.count(), pedidos_antes)
        self.assertEqual(MovimientoInventario.objects.count(), movimientos_antes)

        stock_despues = StockPunto.objects.get(producto=self.producto_a, veterinaria=self.vet_a).cantidad
        self.assertEqual(stock_despues, stock_antes)

    def test_agregar_servicio_sin_mascota_devuelve_error(self):
        self.client.force_login(self.client_a)
        response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "SERVICIO",
                "servicio": self.servicio_a.id_servicio,
                "precio_servicio": self.precio_servicio_a.id_precio,
                "cantidad": "1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("mascota", str(response.data).lower())

    def test_agregar_producto_de_otra_veterinaria_devuelve_error(self):
        self.client.force_login(self.client_a)
        response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto_b.id_producto,
                "cantidad": "1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("veterinaria", str(response.data).lower())

    def test_mascota_de_otro_cliente_en_servicio_devuelve_error(self):
        self.client.force_login(self.client_a)
        response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "SERVICIO",
                "servicio": self.servicio_a.id_servicio,
                "precio_servicio": self.precio_servicio_a.id_precio,
                "mascota": self.mascota_otra_persona.id_mascota,
                "cantidad": "1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente autenticado", str(response.data).lower())

    def test_actualizar_cantidad_recalcula_totales(self):
        self.client.force_login(self.client_a)
        add_response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto_a.id_producto,
                "cantidad": "1",
            },
            format="json",
        )
        detalle_id = add_response.data["detalles"][0]["id_detalle_carrito"]

        update_response = self.client.patch(
            f"/api/gestion/ventas-pagos/carrito/items/{detalle_id}/",
            {"cantidad": "3"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(update_response.data["total_estimado"]), Decimal("150.00"))
        self.assertEqual(Decimal(update_response.data["detalles"][0]["subtotal_estimado"]), Decimal("150.00"))

    def test_vaciar_carrito_deja_total_en_cero(self):
        self.client.force_login(self.client_a)
        self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto_a.id_producto,
                "cantidad": "2",
            },
            format="json",
        )

        vaciar_response = self.client.delete("/api/gestion/ventas-pagos/carrito/vaciar/")
        self.assertEqual(vaciar_response.status_code, status.HTTP_204_NO_CONTENT)

        get_response = self.client.get("/api/gestion/ventas-pagos/carrito/")
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data["detalles"], [])
        self.assertEqual(Decimal(get_response.data["total_estimado"]), Decimal("0"))

    def test_usuario_no_cliente_no_puede_gestionar_carrito(self):
        self.client.force_login(self.admin_a)
        response = self.client.get("/api/gestion/ventas-pagos/carrito/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CU28PaymentsTests(APITestCase):
    def setUp(self):
        self.vet_a = Veterinaria.objects.create(
            nombre="Vet CU28 A",
            slug="vet-cu28-a",
            correo="vet-cu28-a@example.com",
            estado=True
        )
        self.vet_b = Veterinaria.objects.create(
            nombre="Vet CU28 B",
            slug="vet-cu28-b",
            correo="vet-cu28-b@example.com",
            estado=True
        )
        self.rol_client = Rol.objects.get_or_create(nombre=RoleEnum.CLIENT.value, defaults={"descripcion": "Cliente"})[0]
        self.rol_admin = Rol.objects.get_or_create(nombre=RoleEnum.ADMIN.value, defaults={"descripcion": "Admin"})[0]

        self.client_a = User.objects.create(
            correo="cliente-a-cu28@example.com",
            role=self.rol_client,
            veterinaria=self.vet_a,
            is_active=True,
        )
        self.admin_a = User.objects.create(
            correo="admin-a-cu28@example.com",
            role=self.rol_admin,
            veterinaria=self.vet_a,
            is_active=True,
            is_staff=True,
        )
        self.admin_b = User.objects.create(
            correo="admin-b-cu28@example.com",
            role=self.rol_admin,
            veterinaria=self.vet_b,
            is_active=True,
            is_staff=True,
        )

        self.cat_producto = CategoriaProducto.objects.create(
            nombre="Alimentos",
            veterinaria=self.vet_a,
            estado=True,
        )
        self.producto = Producto.objects.create(
            categoria_producto=self.cat_producto,
            nombre="Croquetas",
            precio_venta=Decimal("10.00"),
            visible_catalogo=True,
            estado=True,
            veterinaria=self.vet_a,
        )
        self.punto = PuntoInventario.objects.create(
            veterinaria=self.vet_a,
            tipo=PuntoInventario.TipoPunto.ALMACEN_GENERAL,
            nombre="Almacen Central A",
            estado=True,
        )
        self.stock = StockPunto.objects.create(
            punto_inventario=self.punto,
            producto=self.producto,
            veterinaria=self.vet_a,
            cantidad=Decimal("100.00"),
            cantidad_minima=Decimal("1.00"),
        )
        self.cat_servicio = CategoriaServicio.objects.create(
            nombre="Higiene",
            descripcion="Servicios higiene",
            veterinaria=self.vet_a,
            estado=True,
        )
        self.servicio = Servicio.objects.create(
            nombre="Corte de Pelo",
            descripcion="Corte de pelo para mascotas",
            categoria=self.cat_servicio,
            estado=True,
            veterinaria=self.vet_a,
        )
        self.precio_servicio = PrecioServicio.objects.create(
            servicio=self.servicio,
            variacion="General",
            modalidad="Domicilio",
            precio=Decimal("50.00"),
            estado=True,
            veterinaria=self.vet_a,
        )
        self.especie = Especie.objects.create(nombre="Canino")
        self.raza = Raza.objects.create(nombre="Pug", especie=self.especie)
        self.mascota = Mascota.objects.create(
            usuario=self.client_a,
            especie=self.especie,
            raza=self.raza,
            veterinaria=self.vet_a,
            nombre="Coco",
            fecha_nac=date(2023, 1, 1),
            estado=True,
        )
        self.cita = Cita.objects.create(
            usuario=self.client_a,
            mascota=self.mascota,
            servicio=self.servicio,
            precio_servicio=self.precio_servicio,
            fecha_programada=date.today(),
            hora_inicio="10:00:00",
            hora_fin="11:00:00",
            modalidad="DOMICILIO",
            direccion_cita="Av. Arce #123",
            estado="PENDIENTE",
            veterinaria=self.vet_a,
        )
        self.venta = Venta.objects.create(
            veterinaria=self.vet_a,
            usuario_responsable=self.admin_a,
            cliente=self.client_a,
            mascota=self.mascota,
            subtotal=Decimal("20.00"),
            total=Decimal("20.00"),
            estado_venta=Venta.EstadoVenta.PENDIENTE_COBRO,
        )

    def test_crear_pago_stripe_venta_web(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(
            "/api/gestion/ventas-pagos/pagos/checkout-session/",
            {
                "tipo_referencia": "VENTA_WEB",
                "referencia_id": self.venta.id_venta,
                "metodo_pago": "STRIPE",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("checkout_url", response.data)
        self.assertEqual(response.data["estado_pago"], "PENDIENTE")

        pago = Pago.objects.get(id_pago=response.data["pago_id"])
        self.assertEqual(pago.tipo_referencia, "VENTA_WEB")
        self.assertEqual(pago.referencia_id, self.venta.id_venta)
        self.assertEqual(pago.estado_pago, "PENDIENTE")

    def test_confirmar_pago_manual_venta_web(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(
            "/api/gestion/ventas-pagos/pagos/confirmar-manual/",
            {
                "tipo_referencia": "VENTA_WEB",
                "referencia_id": self.venta.id_venta,
                "metodo_pago": "EFECTIVO",
                "observacion": "Pago manual en caja",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_pago"], "PAGADO")
        self.assertIsNotNone(response.data["codigo_transaccion"])

        self.venta.refresh_from_db()
        self.assertEqual(self.venta.estado_venta, "PAGADA")

        comprobante = ComprobantePago.objects.get(pago_id=response.data["id_pago"])
        self.assertEqual(comprobante.monto, self.venta.total)
        self.assertEqual(comprobante.tipo_comprobante, "RECIBO")
        self.assertEqual(comprobante.estado, "EMITIDO")

    def test_checkout_carrito_temporal_crea_pedido(self):
        self.client.force_login(self.client_a)
        self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto.id_producto,
                "cantidad": "2",
            },
            format="json",
        )

        response = self.client.post(
            "/api/gestion/notificaciones/pedidos/",
            {
                "tipo_entrega": "DOMICILIO",
                "direccion_entrega": "Av. Arce 1234",
                "observacion": "Entregar tarde",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["estado_pedido"], "PENDIENTE")
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("20.00"))
        self.assertEqual(Decimal(response.data["total"]), Decimal("30.00"))

        pedido_id = response.data["id_pedido"]
        checkout_response = self.client.post(
            "/api/gestion/ventas-pagos/pagos/checkout-session/",
            {
                "tipo_referencia": "PEDIDO_MOVIL",
                "referencia_id": pedido_id,
                "metodo_pago": "STRIPE",
            },
            format="json",
        )
        self.assertEqual(checkout_response.status_code, status.HTTP_201_CREATED)

    def test_confirmar_pago_desde_webhook(self):
        pago = Pago.objects.create(
            veterinaria=self.vet_a,
            usuario=self.admin_a,
            tipo_referencia="VENTA_WEB",
            referencia_id=self.venta.id_venta,
            metodo_pago="STRIPE",
            estado_pago="PENDIENTE",
            monto=self.venta.total,
            stripe_session_id="cs_test_123456",
        )

        from unittest.mock import patch
        
        payload = {
            "id": "evt_test_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123456",
                    "object": "checkout.session",
                    "client_reference_id": str(pago.id_pago),
                    "amount_total": 2000,
                    "currency": "usd",
                    "payment_status": "paid",
                    "payment_intent": "pi_test_intent_123",
                }
            }
        }

        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = True
            
            response = self.client.post(
                "/api/gestion/ventas-pagos/pagos/stripe/webhook/",
                payload,
                format="json",
                HTTP_STRIPE_SIGNATURE="t=123,v1=abc",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        pago.refresh_from_db()
        self.assertEqual(pago.estado_pago, "PAGADO")
        self.venta.refresh_from_db()
        self.assertEqual(self.venta.estado_venta, "PAGADA")
        self.assertTrue(ComprobantePago.objects.filter(pago=pago).exists())

    def test_pago_aprobado_sin_stock_deja_pedido_pendiente(self):
        # 1. Crear un pedido con producto
        self.client.force_login(self.client_a)
        self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto.id_producto,
                "cantidad": "10",
            },
            format="json",
        )
        pedido_response = self.client.post(
            "/api/gestion/notificaciones/pedidos/",
            {
                "tipo_entrega": "DOMICILIO",
                "direccion_entrega": "Av. Arce 1234",
            },
            format="json",
        )
        self.assertEqual(pedido_response.status_code, status.HTTP_201_CREATED)
        pedido_id = pedido_response.data["id_pedido"]

        # 2. Dejar el stock a 0 en el almacen central
        self.stock.cantidad = Decimal("0.00")
        self.stock.save()

        # 3. Crear e iniciar el pago
        pago = Pago.objects.create(
            veterinaria=self.vet_a,
            usuario=self.client_a,
            tipo_referencia="PEDIDO_MOVIL",
            referencia_id=pedido_id,
            metodo_pago="STRIPE",
            estado_pago="PENDIENTE",
            monto=Decimal("110.00"),
            stripe_session_id="cs_test_9999",
        )

        # 4. Confirmar el pago por webhook
        from unittest.mock import patch
        payload = {
            "id": "evt_test_999",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_9999",
                    "object": "checkout.session",
                    "client_reference_id": str(pago.id_pago),
                    "amount_total": 11000,
                    "currency": "usd",
                    "payment_status": "paid",
                    "payment_intent": "pi_test_intent_999",
                }
            }
        }

        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = True
            response = self.client.post(
                "/api/gestion/ventas-pagos/pagos/stripe/webhook/",
                payload,
                format="json",
                HTTP_STRIPE_SIGNATURE="t=123,v1=abc",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 5. Verificar que el pago es PAGADO pero el pedido queda PENDIENTE y anotado
        pago.refresh_from_db()
        self.assertEqual(pago.estado_pago, "PAGADO")

        pedido = Pedido.objects.get(id_pedido=pedido_id)
        self.assertEqual(pedido.estado_pedido, "PENDIENTE")
        self.assertIn("REVISION ADMINISTRATIVA", pedido.observacion)
        
        # Verificar que no hay movimientos de salida de inventario
        self.assertFalse(
            MovimientoInventario.objects.filter(
                motivo__contains=f"Despacho Pedido Móvil #{pedido_id}"
            ).exists()
        )

        self.assertTrue(
            Seguimiento.objects.filter(
                pedido_id=pedido_id,
                tipo_seguimiento="PEDIDO",
                estado_actual="PENDIENTE",
                visible_cliente=True,
            ).exists()
        )

    def test_pago_aprobado_crea_seguimiento_publico_para_pedido_confirmado(self):
        self.client.force_login(self.client_a)
        self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto.id_producto,
                "cantidad": "2",
            },
            format="json",
        )
        pedido_response = self.client.post(
            "/api/gestion/notificaciones/pedidos/",
            {
                "tipo_entrega": "RECOJO",
            },
            format="json",
        )
        self.assertEqual(pedido_response.status_code, status.HTTP_201_CREATED)
        pedido_id = pedido_response.data["id_pedido"]

        pago = Pago.objects.create(
            veterinaria=self.vet_a,
            usuario=self.client_a,
            cliente=self.client_a,
            tipo_referencia="PEDIDO_MOVIL",
            referencia_id=pedido_id,
            metodo_pago="STRIPE",
            estado_pago="PENDIENTE",
            monto=Decimal("20.00"),
            stripe_session_id="cs_test_confirmado",
        )

        from unittest.mock import patch

        payload = {
            "id": "evt_test_confirmado",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_confirmado",
                    "object": "checkout.session",
                    "client_reference_id": str(pago.id_pago),
                    "amount_total": 2000,
                    "currency": "bob",
                    "payment_status": "paid",
                    "payment_intent": "pi_test_confirmado",
                }
            },
        }

        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = True
            response = self.client.post(
                "/api/gestion/ventas-pagos/pagos/stripe/webhook/",
                payload,
                format="json",
                HTTP_STRIPE_SIGNATURE="t=123,v1=abc",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            Seguimiento.objects.filter(
                pedido_id=pedido_id,
                tipo_seguimiento="PEDIDO",
                estado_actual="CONFIRMADO",
                visible_cliente=True,
            ).exists()
        )

    def test_evitar_pedidos_duplicados(self):
        # 1. Crear primer pedido
        self.client.force_login(self.client_a)
        self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto.id_producto,
                "cantidad": "1",
            },
            format="json",
        )
        response_1 = self.client.post(
            "/api/gestion/notificaciones/pedidos/",
            {
                "tipo_entrega": "DOMICILIO",
                "direccion_entrega": "Av. Arce 1234",
            },
            format="json",
        )
        self.assertEqual(response_1.status_code, status.HTTP_201_CREATED)
        id_1 = response_1.data["id_pedido"]

        # 2. Intentar crear segundo pedido (debe devolver el primero ya que sigue PENDIENTE)
        response_2 = self.client.post(
            "/api/gestion/notificaciones/pedidos/",
            {
                "tipo_entrega": "DOMICILIO",
                "direccion_entrega": "Av. Arce 1234",
            },
            format="json",
        )
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.assertEqual(response_2.data["id_pedido"], id_1)

    def test_evitar_pago_duplicado(self):
        Pago.objects.create(
            veterinaria=self.vet_a,
            usuario=self.admin_a,
            tipo_referencia="VENTA_WEB",
            referencia_id=self.venta.id_venta,
            metodo_pago="EFECTIVO",
            estado_pago="PAGADO",
            monto=self.venta.total,
        )

        self.client.force_login(self.admin_a)
        response_manual = self.client.post(
            "/api/gestion/ventas-pagos/pagos/confirmar-manual/",
            {
                "tipo_referencia": "VENTA_WEB",
                "referencia_id": self.venta.id_venta,
                "metodo_pago": "EFECTIVO",
            },
            format="json",
        )
        self.assertEqual(response_manual.status_code, status.HTTP_400_BAD_REQUEST)

        response_stripe = self.client.post(
            "/api/gestion/ventas-pagos/pagos/checkout-session/",
            {
                "tipo_referencia": "VENTA_WEB",
                "referencia_id": self.venta.id_venta,
                "metodo_pago": "STRIPE",
            },
            format="json",
        )
        self.assertEqual(response_stripe.status_code, status.HTTP_400_BAD_REQUEST)

    def test_aislamiento_multitenant(self):
        self.client.force_login(self.admin_b)
        
        response_cobro = self.client.post(
            "/api/gestion/ventas-pagos/pagos/confirmar-manual/",
            {
                "tipo_referencia": "VENTA_WEB",
                "referencia_id": self.venta.id_venta,
                "metodo_pago": "EFECTIVO",
            },
            format="json",
        )
        self.assertEqual(response_cobro.status_code, status.HTTP_400_BAD_REQUEST)

        pago = Pago.objects.create(
            veterinaria=self.vet_a,
            usuario=self.admin_a,
            tipo_referencia="VENTA_WEB",
            referencia_id=self.venta.id_venta,
            metodo_pago="EFECTIVO",
            estado_pago="PAGADO",
            monto=self.venta.total,
        )
        comprobante = ComprobantePago.objects.create(
            veterinaria=self.vet_a,
            pago=pago,
            numero_comprobante="REC-000099",
            tipo_comprobante="RECIBO",
            monto=pago.monto,
            metodo_pago=pago.metodo_pago,
        )

        response_ver_pago = self.client.get(f"/api/gestion/ventas-pagos/pagos/{pago.id_pago}/")
        self.assertEqual(response_ver_pago.status_code, status.HTTP_404_NOT_FOUND)

        response_ver_comprobante = self.client.get(f"/api/gestion/ventas-pagos/comprobantes/{comprobante.id_comprobante}/")
        self.assertEqual(response_ver_comprobante.status_code, status.HTTP_404_NOT_FOUND)

    def test_seguridad_no_datos_sensibles(self):
        pago_fields = [f.name for f in Pago._meta.get_fields()]
        self.assertNotIn("tarjeta", pago_fields)
        self.assertNotIn("card", pago_fields)
        self.assertNotIn("cvv", pago_fields)
        self.assertNotIn("pin", pago_fields)
