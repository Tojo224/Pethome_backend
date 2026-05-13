from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.AutenticacionySeguridad.models import Rol, User, Veterinaria
from apps.GestionClientesyMascotas.models import Mascota
from apps.GestionServiciosyReserva.models import (
    CategoriaServicio,
    Cita,
    Especie,
    PrecioServicio,
    Raza,
    Servicio,
)
from apps.GestionarClinicaVeterinaria.models import ConsultaClinica, HistorialClinico

from .models import Pedido, Seguimiento

FERNET_TEST_KEY = "y-8vRXvZL5t7I8S_dZd2a0B7aKXzH_kL8BkpE9SLiW8="


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class CU33SeguimientoPedidosAccessTests(APITestCase):
    def setUp(self):
        self.vet_a = Veterinaria.objects.create(
            nombre="Vet CU33 A",
            slug="vet-cu33-a",
            nit="cu33-a",
            correo="vet-cu33-a@example.com",
        )
        self.vet_b = Veterinaria.objects.create(
            nombre="Vet CU33 B",
            slug="vet-cu33-b",
            nit="cu33-b",
            correo="vet-cu33-b@example.com",
        )

        self.rol_superadmin = Rol.objects.create(nombre="SUPERADMIN", descripcion="Superadmin")
        self.rol_admin = Rol.objects.create(nombre="ADMIN", descripcion="Admin")
        self.rol_veterinarian = Rol.objects.create(nombre="VETERINARIAN", descripcion="Veterinario")
        self.rol_recepcionista = Rol.objects.create(nombre="RECEPCIONISTA", descripcion="Recepcionista")
        self.rol_client = Rol.objects.create(nombre="CLIENT", descripcion="Cliente")

        self.superadmin = User.objects.create(
            correo="superadmin-cu33@example.com",
            role=self.rol_superadmin,
            veterinaria=None,
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )

        self.admin_a = User.objects.create(
            correo="admin-cu33-a@example.com",
            role=self.rol_admin,
            veterinaria=self.vet_a,
            is_active=True,
            is_staff=True,
            is_superuser=False,
        )
        self.recepcionista_a = User.objects.create(
            correo="recep-cu33-a@example.com",
            role=self.rol_recepcionista,
            veterinaria=self.vet_a,
            is_active=True,
            is_staff=True,
            is_superuser=False,
        )
        self.veterinario_a = User.objects.create(
            correo="vet-cu33-a@example.com",
            role=self.rol_veterinarian,
            veterinaria=self.vet_a,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        self.client_a = User.objects.create(
            correo="cliente-cu33-a@example.com",
            role=self.rol_client,
            veterinaria=self.vet_a,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        self.client_a_2 = User.objects.create(
            correo="cliente-cu33-a2@example.com",
            role=self.rol_client,
            veterinaria=self.vet_a,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        self.client_b = User.objects.create(
            correo="cliente-cu33-b@example.com",
            role=self.rol_client,
            veterinaria=self.vet_b,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )

        self.especie = Especie.objects.create(nombre="Canino CU33")
        self.raza = Raza.objects.create(nombre="Mestizo CU33", especie=self.especie)

        self.mascota_a = Mascota.objects.create(
            usuario=self.client_a,
            especie=self.especie,
            raza=self.raza,
            veterinaria=self.vet_a,
            nombre="Firulais A",
        )
        self.mascota_a_2 = Mascota.objects.create(
            usuario=self.client_a_2,
            especie=self.especie,
            raza=self.raza,
            veterinaria=self.vet_a,
            nombre="Firulais A2",
        )
        self.mascota_b = Mascota.objects.create(
            usuario=self.client_b,
            especie=self.especie,
            raza=self.raza,
            veterinaria=self.vet_b,
            nombre="Firulais B",
        )

        self.categoria_a = CategoriaServicio.objects.create(
            nombre="Consulta CU33 A",
            descripcion="Categoria A",
            veterinaria=self.vet_a,
        )
        self.servicio_a = Servicio.objects.create(
            nombre="Servicio CU33 A",
            descripcion="Servicio A",
            categoria=self.categoria_a,
            duracion_estimada=30,
            disponible_domicilio=True,
            veterinaria=self.vet_a,
        )
        self.precio_a = PrecioServicio.objects.create(
            servicio=self.servicio_a,
            variacion="General",
            modalidad="CLINICA",
            precio=50,
            descripcion="Precio A",
            veterinaria=self.vet_a,
        )

        self.categoria_b = CategoriaServicio.objects.create(
            nombre="Consulta CU33 B",
            descripcion="Categoria B",
            veterinaria=self.vet_b,
        )
        self.servicio_b = Servicio.objects.create(
            nombre="Servicio CU33 B",
            descripcion="Servicio B",
            categoria=self.categoria_b,
            duracion_estimada=30,
            disponible_domicilio=True,
            veterinaria=self.vet_b,
        )
        self.precio_b = PrecioServicio.objects.create(
            servicio=self.servicio_b,
            variacion="General",
            modalidad="CLINICA",
            precio=55,
            descripcion="Precio B",
            veterinaria=self.vet_b,
        )

        self.cita_asignada_vet = Cita.objects.create(
            usuario=self.client_a,
            mascota=self.mascota_a,
            servicio=self.servicio_a,
            precio_servicio=self.precio_a,
            fecha_programada=timezone.localdate() + timedelta(days=1),
            hora_inicio=timezone.datetime(2026, 5, 1, 10, 0).time(),
            modalidad="CLINICA",
            estado="PENDIENTE",
            veterinaria=self.vet_a,
        )
        self.cita_no_asignada_vet = Cita.objects.create(
            usuario=self.client_a_2,
            mascota=self.mascota_a_2,
            servicio=self.servicio_a,
            precio_servicio=self.precio_a,
            fecha_programada=timezone.localdate() + timedelta(days=2),
            hora_inicio=timezone.datetime(2026, 5, 1, 11, 0).time(),
            modalidad="CLINICA",
            estado="PENDIENTE",
            veterinaria=self.vet_a,
        )
        self.cita_tenant_b = Cita.objects.create(
            usuario=self.client_b,
            mascota=self.mascota_b,
            servicio=self.servicio_b,
            precio_servicio=self.precio_b,
            fecha_programada=timezone.localdate() + timedelta(days=2),
            hora_inicio=timezone.datetime(2026, 5, 1, 12, 0).time(),
            modalidad="CLINICA",
            estado="PENDIENTE",
            veterinaria=self.vet_b,
        )

        self.historial_a = HistorialClinico.objects.create(mascota=self.mascota_a)
        ConsultaClinica.objects.create(
            historial_clinico=self.historial_a,
            cita=self.cita_asignada_vet,
            usuario_veterinario=self.veterinario_a,
            motivo_consulta="Consulta asignada",
            fecha_consulta=timezone.now(),
            veterinaria=self.vet_a,
        )

        self.pedido_a_cliente = Pedido.objects.create(
            usuario=self.client_a,
            veterinaria=self.vet_a,
            tipo_entrega="DOMICILIO",
            estado_pedido="EN_PREPARACION",
            subtotal=100,
            costo_envio=10,
            total=110,
        )
        self.pedido_a_otro_cliente = Pedido.objects.create(
            usuario=self.client_a_2,
            veterinaria=self.vet_a,
            tipo_entrega="RECOJO",
            estado_pedido="PENDIENTE",
            subtotal=80,
            costo_envio=0,
            total=80,
        )
        self.pedido_b = Pedido.objects.create(
            usuario=self.client_b,
            veterinaria=self.vet_b,
            tipo_entrega="DOMICILIO",
            estado_pedido="CONFIRMADO",
            subtotal=120,
            costo_envio=15,
            total=135,
        )

        self.seg_pedido_publico_cliente_a = Seguimiento.objects.create(
            veterinaria=self.vet_a,
            usuario=self.recepcionista_a,
            pedido=self.pedido_a_cliente,
            tipo_seguimiento="PEDIDO",
            estado_anterior="PENDIENTE",
            estado_actual="EN_PREPARACION",
            descripcion="Pedido en preparacion",
            visible_cliente=True,
        )
        self.seg_pedido_interno_cliente_a = Seguimiento.objects.create(
            veterinaria=self.vet_a,
            usuario=self.recepcionista_a,
            pedido=self.pedido_a_cliente,
            tipo_seguimiento="PEDIDO",
            estado_anterior="EN_PREPARACION",
            estado_actual="EN_CAMINO",
            descripcion="Nota interna",
            visible_cliente=False,
        )
        self.seg_cita_publico_asignada = Seguimiento.objects.create(
            veterinaria=self.vet_a,
            usuario=self.veterinario_a,
            cita=self.cita_asignada_vet,
            tipo_seguimiento="CITA",
            estado_anterior="PENDIENTE",
            estado_actual="CONFIRMADA",
            descripcion="Cita confirmada",
            visible_cliente=True,
        )
        self.seg_cita_interno_asignada = Seguimiento.objects.create(
            veterinaria=self.vet_a,
            usuario=self.veterinario_a,
            cita=self.cita_asignada_vet,
            tipo_seguimiento="SERVICIO",
            estado_anterior="CONFIRMADA",
            estado_actual="EN_ATENCION",
            descripcion="Observacion interna veterinaria",
            visible_cliente=False,
        )
        self.seg_cita_publico_no_asignada = Seguimiento.objects.create(
            veterinaria=self.vet_a,
            usuario=self.recepcionista_a,
            cita=self.cita_no_asignada_vet,
            tipo_seguimiento="CITA",
            estado_anterior="PENDIENTE",
            estado_actual="REPROGRAMADA",
            descripcion="Cita de otro cliente",
            visible_cliente=True,
        )
        self.seg_tenant_b = Seguimiento.objects.create(
            veterinaria=self.vet_b,
            usuario=self.client_b,
            pedido=self.pedido_b,
            tipo_seguimiento="PEDIDO",
            estado_anterior="PENDIENTE",
            estado_actual="CONFIRMADO",
            descripcion="Seguimiento de otro tenant",
            visible_cliente=True,
        )

        now = timezone.now()
        Pedido.objects.filter(id_pedido=self.pedido_a_cliente.id_pedido).update(
            fecha_pedido=now - timedelta(days=2)
        )
        Pedido.objects.filter(id_pedido=self.pedido_a_otro_cliente.id_pedido).update(
            fecha_pedido=now - timedelta(days=1)
        )
        Pedido.objects.filter(id_pedido=self.pedido_b.id_pedido).update(
            fecha_pedido=now - timedelta(hours=12)
        )
        Seguimiento.objects.filter(id_seguimiento=self.seg_cita_publico_asignada.id_seguimiento).update(
            fecha_hora=now - timedelta(hours=4)
        )
        Seguimiento.objects.filter(id_seguimiento=self.seg_cita_publico_no_asignada.id_seguimiento).update(
            fecha_hora=now - timedelta(hours=5)
        )
        Seguimiento.objects.filter(id_seguimiento=self.seg_pedido_publico_cliente_a.id_seguimiento).update(
            fecha_hora=now - timedelta(hours=3)
        )
        Seguimiento.objects.filter(id_seguimiento=self.seg_pedido_interno_cliente_a.id_seguimiento).update(
            fecha_hora=now - timedelta(hours=2)
        )
        Seguimiento.objects.filter(id_seguimiento=self.seg_cita_interno_asignada.id_seguimiento).update(
            fecha_hora=now - timedelta(hours=1)
        )

        self.pedido_list_url = "/api/gestion/notificaciones/pedidos/"
        self.seguimiento_list_url = "/api/gestion/notificaciones/seguimientos/"

    def _pedido_detail_url(self, pedido_id):
        return f"/api/gestion/notificaciones/pedidos/{pedido_id}/"

    def _seguimiento_detail_url(self, seguimiento_id):
        return f"/api/gestion/notificaciones/seguimientos/{seguimiento_id}/"

    def test_01_unauthenticated_user_gets_401(self):
        response = self.client.get(self.pedido_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_02_superadmin_gets_403_for_list_and_detail(self):
        self.client.force_login(self.superadmin)

        list_response = self.client.get(self.seguimiento_list_url)
        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)

        detail_response = self.client.get(self._seguimiento_detail_url(self.seg_cita_publico_asignada.id_seguimiento))
        self.assertEqual(detail_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_03_client_lists_only_own_orders_and_followups(self):
        self.client.force_login(self.client_a)

        pedidos_response = self.client.get(self.pedido_list_url)
        self.assertEqual(pedidos_response.status_code, status.HTTP_200_OK)
        pedidos_ids = {item["id_pedido"] for item in pedidos_response.data}
        self.assertSetEqual(pedidos_ids, {self.pedido_a_cliente.id_pedido})

        seguimientos_response = self.client.get(self.seguimiento_list_url)
        self.assertEqual(seguimientos_response.status_code, status.HTTP_200_OK)
        seguimientos_ids = {item["id_seguimiento"] for item in seguimientos_response.data}
        self.assertSetEqual(
            seguimientos_ids,
            {self.seg_pedido_publico_cliente_a.id_seguimiento, self.seg_cita_publico_asignada.id_seguimiento},
        )

    def test_04_client_cannot_view_foreign_detail_and_gets_404(self):
        self.client.force_login(self.client_a)

        pedido_response = self.client.get(self._pedido_detail_url(self.pedido_a_otro_cliente.id_pedido))
        self.assertEqual(pedido_response.status_code, status.HTTP_404_NOT_FOUND)

        seguimiento_response = self.client.get(self._seguimiento_detail_url(self.seg_cita_publico_no_asignada.id_seguimiento))
        self.assertEqual(seguimiento_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_05_client_never_sees_visible_cliente_false(self):
        self.client.force_login(self.client_a)

        seguimiento_list_response = self.client.get(self.seguimiento_list_url)
        self.assertEqual(seguimiento_list_response.status_code, status.HTTP_200_OK)
        ids = {item["id_seguimiento"] for item in seguimiento_list_response.data}
        self.assertNotIn(self.seg_pedido_interno_cliente_a.id_seguimiento, ids)
        self.assertNotIn(self.seg_cita_interno_asignada.id_seguimiento, ids)

        pedido_detail_response = self.client.get(self._pedido_detail_url(self.pedido_a_cliente.id_pedido))
        self.assertEqual(pedido_detail_response.status_code, status.HTTP_200_OK)
        nested_ids = {item["id_seguimiento"] for item in pedido_detail_response.data["seguimientos"]}
        self.assertIn(self.seg_pedido_publico_cliente_a.id_seguimiento, nested_ids)
        self.assertNotIn(self.seg_pedido_interno_cliente_a.id_seguimiento, nested_ids)

    def test_06_admin_sees_data_of_own_tenant(self):
        self.client.force_login(self.admin_a)

        pedidos_response = self.client.get(self.pedido_list_url)
        self.assertEqual(pedidos_response.status_code, status.HTTP_200_OK)
        pedidos_ids = {item["id_pedido"] for item in pedidos_response.data}
        self.assertSetEqual(pedidos_ids, {self.pedido_a_cliente.id_pedido, self.pedido_a_otro_cliente.id_pedido})

        seguimientos_response = self.client.get(self.seguimiento_list_url)
        self.assertEqual(seguimientos_response.status_code, status.HTTP_200_OK)
        seguimientos_ids = {item["id_seguimiento"] for item in seguimientos_response.data}
        self.assertIn(self.seg_pedido_interno_cliente_a.id_seguimiento, seguimientos_ids)
        self.assertIn(self.seg_cita_interno_asignada.id_seguimiento, seguimientos_ids)

    def test_07_admin_does_not_see_data_from_other_tenant(self):
        self.client.force_login(self.admin_a)

        pedidos_response = self.client.get(self.pedido_list_url)
        pedidos_ids = {item["id_pedido"] for item in pedidos_response.data}
        self.assertNotIn(self.pedido_b.id_pedido, pedidos_ids)

        seguimientos_response = self.client.get(self.seguimiento_list_url)
        seguimientos_ids = {item["id_seguimiento"] for item in seguimientos_response.data}
        self.assertNotIn(self.seg_tenant_b.id_seguimiento, seguimientos_ids)

    def test_08_recepcionista_sees_data_of_own_tenant(self):
        self.client.force_login(self.recepcionista_a)

        pedidos_response = self.client.get(self.pedido_list_url)
        self.assertEqual(pedidos_response.status_code, status.HTTP_200_OK)
        pedidos_ids = {item["id_pedido"] for item in pedidos_response.data}
        self.assertSetEqual(pedidos_ids, {self.pedido_a_cliente.id_pedido, self.pedido_a_otro_cliente.id_pedido})

        seguimientos_response = self.client.get(self.seguimiento_list_url)
        self.assertEqual(seguimientos_response.status_code, status.HTTP_200_OK)
        seguimientos_ids = {item["id_seguimiento"] for item in seguimientos_response.data}
        self.assertIn(self.seg_pedido_interno_cliente_a.id_seguimiento, seguimientos_ids)

    def test_09_veterinarian_sees_only_assigned_cita_servicio(self):
        self.client.force_login(self.veterinario_a)

        response = self.client.get(self.seguimiento_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id_seguimiento"] for item in response.data}
        self.assertIn(self.seg_cita_publico_asignada.id_seguimiento, ids)
        self.assertIn(self.seg_cita_interno_asignada.id_seguimiento, ids)
        self.assertNotIn(self.seg_cita_publico_no_asignada.id_seguimiento, ids)
        self.assertNotIn(self.seg_pedido_publico_cliente_a.id_seguimiento, ids)

    def test_10_veterinarian_cannot_see_unrelated_orders(self):
        self.client.force_login(self.veterinario_a)

        list_response = self.client.get(self.pedido_list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 0)

        detail_response = self.client.get(self._pedido_detail_url(self.pedido_a_cliente.id_pedido))
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_11_invalid_date_range_returns_400(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            self.pedido_list_url,
            {"fecha_desde": "2026-05-10", "fecha_hasta": "2026-05-01"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)
        self.assertIn("fecha_hasta", response.data["errors"])

    def test_12_unknown_query_param_returns_400(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(self.seguimiento_list_url, {"foo": "bar"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)
        self.assertIn("query_params", response.data["errors"])

    def test_13_lists_are_sorted_newest_to_oldest(self):
        self.client.force_login(self.admin_a)

        pedidos_response = self.client.get(self.pedido_list_url)
        self.assertEqual(pedidos_response.status_code, status.HTTP_200_OK)
        pedidos_ids = [item["id_pedido"] for item in pedidos_response.data]
        self.assertEqual(pedidos_ids, [self.pedido_a_otro_cliente.id_pedido, self.pedido_a_cliente.id_pedido])

        seguimientos_response = self.client.get(self.seguimiento_list_url)
        self.assertEqual(seguimientos_response.status_code, status.HTTP_200_OK)
        seguimiento_ids = [item["id_seguimiento"] for item in seguimientos_response.data]
        self.assertEqual(
            seguimiento_ids,
            [
                self.seg_cita_interno_asignada.id_seguimiento,
                self.seg_pedido_interno_cliente_a.id_seguimiento,
                self.seg_pedido_publico_cliente_a.id_seguimiento,
                self.seg_cita_publico_asignada.id_seguimiento,
                self.seg_cita_publico_no_asignada.id_seguimiento,
            ],
        )
