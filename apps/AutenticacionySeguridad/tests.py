from django.db import connection
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .enums.roles import RoleEnum
from .models import Bitacora, Rol, User, Veterinaria
from .services.bitacora_register_service import BitacoraService

FERNET_TEST_KEY = "y-8vRXvZL5t7I8S_dZd2a0B7aKXzH_kL8BkpE9SLiW8="
FERNET_OTHER_KEY = "1f6Oqs5q8SwknfImHo98B8E3uI4xg3Vd3X2wU_0wC1Q="


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class AuthFlowTests(APITestCase):
	def setUp(self):
		self.vet = Veterinaria.objects.create(
			nombre="Vet Demo",
			slug="vet-demo",
			nit="123",
			correo="vet@example.com",
		)
		self.rol_admin = Rol.objects.create(
			nombre=RoleEnum.ADMIN.value,
			descripcion="Administrador",
		)
		self.user = User.objects.create(
			correo="admin_test@example.com",
			role=self.rol_admin,
			veterinaria=self.vet,
			is_active=True,
			is_staff=True,
			is_superuser=True,
		)
		self.user.set_password("Admin12345!")
		self.user.save()

	def _login(self):
		return self.client.post(
			"/api/auth/login/",
			{
				"correo": self.user.correo,
				"password": "Admin12345!",
			},
			format="json",
		)

	def test_login_response_supports_root_and_nested_tokens(self):
		response = self._login()

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("tokens", response.data)
		self.assertIn("access", response.data)
		self.assertIn("refresh", response.data)
		self.assertEqual(response.data["access"], response.data["tokens"]["access"])
		self.assertEqual(response.data["refresh"], response.data["tokens"]["refresh"])

	def test_admin_can_access_bitacora_and_logout_with_login_tokens(self):
		login_response = self._login()
		access_token = login_response.data["access"]
		refresh_token = login_response.data["refresh"]

		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

		bitacora_response = self.client.get("/api/auth/bitacora/")
		self.assertEqual(bitacora_response.status_code, status.HTTP_200_OK)

		logout_response = self.client.post(
			"/api/auth/logout/",
			{"refresh": refresh_token},
			format="json",
		)
		self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

	def test_admin_can_access_bitacora_with_server_session_after_login(self):
		self._login()

		self.client.credentials()
		bitacora_response = self.client.get("/api/auth/bitacora/")
		self.assertEqual(bitacora_response.status_code, status.HTTP_200_OK)

	def test_logout_without_refresh_closes_server_session(self):
		self._login()

		self.client.credentials()
		logout_response = self.client.post("/api/auth/logout/", {}, format="json")
		self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
		self.assertIn("No se recibió refresh", logout_response.data["detail"])

	def test_bitacora_payload_is_encrypted_and_readable(self):
		BitacoraService.registrar_evento(
			accion="LOGIN",
			descripcion="Prueba",
			usuario=self.user,
			modulo="autenticacion",
			resultado="EXITO",
		)
		log = Bitacora.objects.first()
		self.assertIsInstance(log.payload, dict)
		self.assertEqual(log.payload.get("accion"), "LOGIN")

		with connection.cursor() as cursor:
			cursor.execute(
				"SELECT payload FROM bitacora WHERE id_bitacora = %s",
				[log.id_bitacora],
			)
			raw_payload = cursor.fetchone()[0]

		raw_bytes = bytes(raw_payload)
		self.assertIsInstance(raw_payload, (bytes, memoryview))
		self.assertNotIn(b"LOGIN", raw_bytes)

	def test_bitacora_payload_invalid_key_returns_error(self):
		BitacoraService.registrar_evento(
			accion="LOGIN",
			descripcion="Prueba",
			usuario=self.user,
			modulo="autenticacion",
			resultado="EXITO",
		)
		log = Bitacora.objects.first()

		with self.settings(BITACORA_SECRET_KEYS=[FERNET_OTHER_KEY]):
			refreshed = Bitacora.objects.get(pk=log.pk)
			self.assertEqual(
				refreshed.payload.get("error"),
				"No se pudo descifrar el payload",
			)
