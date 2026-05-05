from datetime import date

from django.test import override_settings
from rest_framework.test import APITestCase

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models import Rol, User, Veterinaria
from apps.GestionClientesyMascotas.models import Especie, Mascota, Raza

FERNET_TEST_KEY = "y-8vRXvZL5t7I8S_dZd2a0B7aKXzH_kL8BkpE9SLiW8="


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class MascotaTenantTests(APITestCase):
	def setUp(self):
		self.vet_a = Veterinaria.objects.create(
			nombre="Vet A",
			slug="vet-a",
			nit="111",
			correo="vet-a@example.com",
		)
		self.vet_b = Veterinaria.objects.create(
			nombre="Vet B",
			slug="vet-b",
			nit="222",
			correo="vet-b@example.com",
		)

		self.rol_admin = Rol.objects.create(
			nombre=RoleEnum.ADMIN.value,
			descripcion="Administrador",
		)
		self.rol_client = Rol.objects.create(
			nombre=RoleEnum.CLIENT.value,
			descripcion="Cliente",
		)

		self.admin_a = User.objects.create(
			correo="admin-a@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=True,
			is_superuser=True,
		)
		self.admin_a.set_password("Admin12345!")
		self.admin_a.save()

		self.admin_b = User.objects.create(
			correo="admin-b@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_b,
			is_active=True,
			is_staff=True,
			is_superuser=True,
		)
		self.admin_b.set_password("Admin12345!")
		self.admin_b.save()

		self.client_a = User.objects.create(
			correo="cliente-a@example.com",
			role=self.rol_client,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=False,
			is_superuser=False,
		)
		self.client_b = User.objects.create(
			correo="cliente-b@example.com",
			role=self.rol_client,
			veterinaria=self.vet_b,
			is_active=True,
			is_staff=False,
			is_superuser=False,
		)

		self.especie = Especie.objects.create(nombre="Canino")
		self.raza = Raza.objects.create(nombre="Labrador", especie=self.especie)

		self.mascota_a = Mascota.objects.create(
			usuario=self.client_a,
			especie=self.especie,
			raza=self.raza,
			veterinaria=self.vet_a,
			nombre="Firulais",
			fecha_nac=date(2023, 1, 1),
		)
		self.mascota_b = Mascota.objects.create(
			usuario=self.client_b,
			especie=self.especie,
			raza=self.raza,
			veterinaria=self.vet_b,
			nombre="Luna",
			fecha_nac=date(2023, 2, 1),
		)

	def test_mascotas_list_is_tenant_scoped(self):
		self.client.force_login(self.admin_a)
		response = self.client.get("/api/gestion/clientes/mascotas/")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["id_mascota"], self.mascota_a.id_mascota)

		self.client.force_login(self.admin_b)
		response = self.client.get("/api/gestion/clientes/mascotas/")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["id_mascota"], self.mascota_b.id_mascota)

	def test_mascota_detail_other_tenant_returns_404(self):
		self.client.force_login(self.admin_a)
		response = self.client.get(
			f"/api/gestion/clientes/mascotas/{self.mascota_b.id_mascota}/"
		)
		self.assertEqual(response.status_code, 404)
