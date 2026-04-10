from rest_framework import status
from rest_framework.test import APITestCase

from .enums.roles import RoleEnum
from .models import Rol, User


class AuthFlowTests(APITestCase):
	def setUp(self):
		self.rol_admin = Rol.objects.create(
			nombre=RoleEnum.ADMIN.value,
			descripcion="Administrador",
		)

		self.user = User.objects.create(
			correo="admin_test@example.com",
			role=self.rol_admin,
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

	def test_admin_can_access_no_slash_endpoints(self):
		login_response = self._login()
		access_token = login_response.data["access"]
		refresh_token = login_response.data["refresh"]

		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

		bitacora_response = self.client.get("/api/auth/bitacora")
		self.assertEqual(bitacora_response.status_code, status.HTTP_200_OK)

		logout_response = self.client.post(
			"/api/auth/logout",
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
