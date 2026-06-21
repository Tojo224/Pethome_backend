from datetime import date, timedelta, time
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models import Perfil, Rol, User, Veterinaria
from apps.GestionClientesyMascotas.models import Mascota
from apps.GestionInventarioProveedores.models import CategoriaProducto, Producto
from apps.GestionServiciosyReserva.models import (
    CategoriaServicio,
    Cita,
    Especie,
    PrecioServicio,
    Raza,
    Servicio,
)
from apps.GestiondeVentasyPagos.models import ComprobantePago, DetalleVenta, Pago, TransaccionPago, Venta
from apps.NotificacionesySeguimiento.models import DetallePedido, Pedido


class HistorialTransaccionesTests(APITestCase):
    maxDiff = None

    def setUp(self):
        self.vet_a = Veterinaria.objects.create(
            nombre="Vet Historial A",
            slug="vet-historial-a",
            correo="vet-a@example.com",
        )
        self.vet_b = Veterinaria.objects.create(
            nombre="Vet Historial B",
            slug="vet-historial-b",
            correo="vet-b@example.com",
        )

        self.rol_admin = Rol.objects.create(nombre=RoleEnum.ADMIN.value, descripcion="Admin")
        self.rol_client = Rol.objects.create(nombre=RoleEnum.CLIENT.value, descripcion="Cliente")

        self.admin_a = self._create_user(
            correo="admin-a-historial@example.com",
            role=self.rol_admin,
            veterinaria=self.vet_a,
            nombre="Admin A",
            is_staff=True,
        )
        self.admin_b = self._create_user(
            correo="admin-b-historial@example.com",
            role=self.rol_admin,
            veterinaria=self.vet_b,
            nombre="Admin B",
            is_staff=True,
        )
        self.client_a = self._create_user(
            correo="cliente-a-historial@example.com",
            role=self.rol_client,
            veterinaria=self.vet_a,
            nombre="Cliente A",
        )
        self.client_b = self._create_user(
            correo="cliente-b-historial@example.com",
            role=self.rol_client,
            veterinaria=self.vet_b,
            nombre="Cliente B",
        )

        self.especie = Especie.objects.create(nombre="Canino Historial")
        self.raza = Raza.objects.create(nombre="Mestizo Historial", especie=self.especie)
        self.mascota_a = Mascota.objects.create(
            usuario=self.client_a,
            especie=self.especie,
            raza=self.raza,
            veterinaria=self.vet_a,
            nombre="Firulais Historial",
            fecha_nac=date(2022, 1, 1),
            estado=True,
        )

        self.categoria_producto = CategoriaProducto.objects.create(
            nombre="Categoria Historial",
            veterinaria=self.vet_a,
            estado=True,
        )
        self.producto = Producto.objects.create(
            categoria_producto=self.categoria_producto,
            nombre="Alimento Historial",
            precio_venta=Decimal("40.00"),
            visible_catalogo=True,
            estado=True,
            veterinaria=self.vet_a,
        )

        self.categoria_servicio = CategoriaServicio.objects.create(
            nombre="Categoria Servicio Historial",
            descripcion="Servicios",
            veterinaria=self.vet_a,
            estado=True,
        )
        self.servicio = Servicio.objects.create(
            nombre="Banio Historial",
            descripcion="Banio premium",
            categoria=self.categoria_servicio,
            estado=True,
            veterinaria=self.vet_a,
        )
        self.precio_servicio = PrecioServicio.objects.create(
            servicio=self.servicio,
            variacion="General",
            modalidad="Clinica",
            precio=Decimal("80.00"),
            estado=True,
            veterinaria=self.vet_a,
        )

        self.venta = Venta.objects.create(
            veterinaria=self.vet_a,
            usuario_responsable=self.admin_a,
            cliente=self.client_a,
            mascota=self.mascota_a,
            subtotal=Decimal("80.00"),
            total=Decimal("80.00"),
            estado_venta=Venta.EstadoVenta.PAGADA,
            observacion="Venta administrada",
        )
        DetalleVenta.objects.create(
            venta=self.venta,
            tipo_item=DetalleVenta.TipoItem.PRODUCTO,
            producto=self.producto,
            descripcion_item="Alimento Historial",
            cantidad=Decimal("2.00"),
            precio_unitario=Decimal("40.00"),
            subtotal=Decimal("80.00"),
            estado=True,
        )

        self.pedido = Pedido.objects.create(
            usuario=self.client_a,
            veterinaria=self.vet_a,
            estado_pedido="CONFIRMADO",
            subtotal=Decimal("120.00"),
            total=Decimal("120.00"),
            observacion="Pedido movil",
        )
        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=3,
            precio_unitario=Decimal("40.00"),
            subtotal=Decimal("120.00"),
            estado=True,
        )

        self.cita = Cita.objects.create(
            usuario=self.client_a,
            mascota=self.mascota_a,
            servicio=self.servicio,
            precio_servicio=self.precio_servicio,
            fecha_programada=date.today(),
            hora_inicio=time(10, 0),
            modalidad=Cita.ModalidadChoices.CLINICA,
            descripcion="Control general",
            estado=Cita.EstadoChoices.PENDIENTE,
            veterinaria=self.vet_a,
        )

        now = timezone.now()
        yesterday = now - timedelta(days=1)

        self.pago_venta = Pago.objects.create(
            veterinaria=self.vet_a,
            usuario=self.admin_a,
            cliente=None,
            tipo_referencia=Pago.TipoReferencia.VENTA_WEB,
            referencia_id=self.venta.id_venta,
            metodo_pago=Pago.MetodoPago.QR,
            estado_pago=Pago.EstadoPago.PAGADO,
            monto=self.venta.total,
            codigo_transaccion="TRX-VENTA-001",
            observacion="Pago de venta",
            fecha_confirmacion=now,
        )
        self.pago_pedido = Pago.objects.create(
            veterinaria=self.vet_a,
            usuario=self.admin_a,
            cliente=None,
            tipo_referencia=Pago.TipoReferencia.PEDIDO_MOVIL,
            referencia_id=self.pedido.id_pedido,
            metodo_pago=Pago.MetodoPago.TRANSFERENCIA,
            estado_pago=Pago.EstadoPago.PAGADO,
            monto=self.pedido.total,
            codigo_transaccion="TRX-PEDIDO-001",
            observacion="Pago de pedido",
            fecha_confirmacion=yesterday,
        )
        self.pago_cita = Pago.objects.create(
            veterinaria=self.vet_a,
            usuario=self.admin_a,
            cliente=None,
            tipo_referencia=Pago.TipoReferencia.CITA_SERVICIO,
            referencia_id=self.cita.id_cita,
            metodo_pago=Pago.MetodoPago.EFECTIVO,
            estado_pago=Pago.EstadoPago.PAGADO,
            monto=self.precio_servicio.precio,
            codigo_transaccion="TRX-CITA-001",
            observacion="Pago de cita",
            fecha_confirmacion=now,
        )
        self.pago_sin_referencia = Pago.objects.create(
            veterinaria=self.vet_a,
            usuario=self.admin_a,
            cliente=None,
            tipo_referencia=Pago.TipoReferencia.VENTA_WEB,
            referencia_id=999999,
            metodo_pago=Pago.MetodoPago.ADMINISTRATIVO,
            estado_pago=Pago.EstadoPago.EN_PROCESO,
            monto=Decimal("15.00"),
            codigo_transaccion="TRX-MISSING-001",
            observacion="Pago sin referencia",
        )
        self.pago_otro_tenant = Pago.objects.create(
            veterinaria=self.vet_b,
            usuario=self.admin_b,
            cliente=self.client_b,
            tipo_referencia=Pago.TipoReferencia.VENTA_WEB,
            referencia_id=321,
            metodo_pago=Pago.MetodoPago.QR,
            estado_pago=Pago.EstadoPago.PAGADO,
            monto=Decimal("50.00"),
            codigo_transaccion="TRX-OTHER-001",
            observacion="Otro tenant",
            fecha_confirmacion=now,
        )

        TransaccionPago.objects.create(
            pago=self.pago_venta,
            veterinaria=self.vet_a,
            provider="MANUAL",
            provider_reference="REF-VENTA-001",
            estado="PAGADO",
            monto=self.pago_venta.monto,
        )
        TransaccionPago.objects.create(
            pago=self.pago_pedido,
            veterinaria=self.vet_a,
            provider="MANUAL",
            provider_reference="REF-PEDIDO-001",
            estado="PAGADO",
            monto=self.pago_pedido.monto,
        )
        TransaccionPago.objects.create(
            pago=self.pago_cita,
            veterinaria=self.vet_a,
            provider="MANUAL",
            provider_reference="REF-CITA-001",
            estado="PAGADO",
            monto=self.pago_cita.monto,
        )

        self.comprobante_venta = ComprobantePago.objects.create(
            veterinaria=self.vet_a,
            pago=self.pago_venta,
            numero_comprobante="REC-000001",
            tipo_comprobante=ComprobantePago.TipoComprobante.RECIBO,
            monto=self.pago_venta.monto,
            metodo_pago=self.pago_venta.metodo_pago,
            detalle_items={},
            estado=ComprobantePago.EstadoComprobante.EMITIDO,
        )

    def _create_user(self, *, correo, role, veterinaria, nombre, is_staff=False):
        user = User.objects.create(
            correo=correo,
            role=role,
            veterinaria=veterinaria,
            is_active=True,
            is_staff=is_staff,
        )
        Perfil.objects.create(usuario=user, nombre=nombre, estado=True)
        return user

    def test_admin_lista_historial_solo_de_su_tenant(self):
        self.client.force_login(self.admin_a)

        response = self.client.get("/api/gestion/ventas-pagos/historial-transacciones/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 4)

        ids = [item["id_pago"] for item in response.data["results"]]
        self.assertIn(self.pago_venta.id_pago, ids)
        self.assertIn(self.pago_pedido.id_pago, ids)
        self.assertIn(self.pago_cita.id_pago, ids)
        self.assertIn(self.pago_sin_referencia.id_pago, ids)
        self.assertNotIn(self.pago_otro_tenant.id_pago, ids)

    def test_cliente_no_puede_ver_historial(self):
        self.client.force_login(self.client_a)

        response = self.client.get("/api/gestion/ventas-pagos/historial-transacciones/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detalle_venta_resuelve_cliente_items_y_comprobante(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            f"/api/gestion/ventas-pagos/historial-transacciones/{self.pago_venta.id_pago}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id_pago"], self.pago_venta.id_pago)
        self.assertEqual(response.data["cliente"]["id"], self.client_a.id_usuario)
        self.assertEqual(response.data["cliente"]["nombre"], "Cliente A")
        self.assertEqual(response.data["estado_pago"], Pago.EstadoPago.PAGADO)
        self.assertEqual(response.data["estado_referencia"], Venta.EstadoVenta.PAGADA)
        self.assertEqual(response.data["referencia_pasarela"], "REF-VENTA-001")
        self.assertEqual(response.data["comprobante"]["id_comprobante"], self.comprobante_venta.id_comprobante)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["descripcion"], "Alimento Historial")

    def test_detalle_pedido_resuelve_cliente_desde_pedido(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            f"/api/gestion/ventas-pagos/historial-transacciones/{self.pago_pedido.id_pago}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cliente"]["id"], self.client_a.id_usuario)
        self.assertEqual(response.data["cliente"]["nombre"], "Cliente A")
        self.assertEqual(response.data["estado_referencia"], "CONFIRMADO")
        self.assertEqual(response.data["items"][0]["tipo"], "PRODUCTO")

    def test_detalle_cita_resuelve_cliente_y_estado_referencia(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            f"/api/gestion/ventas-pagos/historial-transacciones/{self.pago_cita.id_pago}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cliente"]["id"], self.client_a.id_usuario)
        self.assertEqual(response.data["estado_pago"], Pago.EstadoPago.PAGADO)
        self.assertEqual(response.data["estado_referencia"], Cita.EstadoChoices.PENDIENTE)
        self.assertEqual(response.data["items"][0]["tipo"], "SERVICIO")

    def test_filtros_por_estado_pago_tipo_metodo_y_fecha(self):
        self.client.force_login(self.admin_a)

        fecha_hoy = timezone.localdate().isoformat()
        response = self.client.get(
            "/api/gestion/ventas-pagos/historial-transacciones/",
            {
                "estado_pago": Pago.EstadoPago.PAGADO,
                "tipo_referencia": Pago.TipoReferencia.VENTA_WEB,
                "metodo_pago": Pago.MetodoPago.QR,
                "fecha_inicio": fecha_hoy,
                "fecha_fin": fecha_hoy,
                "estado_referencia": Venta.EstadoVenta.PAGADA,
                "cliente": self.client_a.id_usuario,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id_pago"], self.pago_venta.id_pago)

    def test_detalle_con_referencia_inexistente_devuelve_respuesta_controlada(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            f"/api/gestion/ventas-pagos/historial-transacciones/{self.pago_sin_referencia.id_pago}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id_pago"], self.pago_sin_referencia.id_pago)
        self.assertIsNone(response.data["estado_referencia"])
        self.assertEqual(response.data["items"], [])
        self.assertIn("Referencia no disponible", response.data["concepto"])

