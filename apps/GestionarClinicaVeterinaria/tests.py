from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models import (
	ComponenteSistema,
	GrupoPermisoComponente,
	GrupoUsuario,
	Perfil,
	Rol,
	User,
	UsuarioGrupo,
	Veterinaria,
)
from apps.GestionClientesyMascotas.models import Especie, Mascota, Raza

FERNET_TEST_KEY = "y-8vRXvZL5t7I8S_dZd2a0B7aKXzH_kL8BkpE9SLiW8="


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class VeterinarioTenantTests(APITestCase):
	def setUp(self):
		self.vet_a = Veterinaria.objects.create(
			nombre="Vet Clinica A",
			slug="vet-clinica-a",
			nit="301",
			correo="clinica-a@example.com",
		)
		self.vet_b = Veterinaria.objects.create(
			nombre="Vet Clinica B",
			slug="vet-clinica-b",
			nit="302",
			correo="clinica-b@example.com",
		)

		self.rol_admin = Rol.objects.create(
			nombre=RoleEnum.ADMIN.value,
			descripcion="Administrador",
		)
		self.rol_vet = Rol.objects.create(
			nombre=RoleEnum.VETERINARIAN.value,
			descripcion="Veterinario",
		)

		self.admin = User.objects.create(
			correo="admin-clinica@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=True,
			is_superuser=False,
		)
		self.admin.set_password("Admin12345!")
		self.admin.save()

		vet_a_user = User.objects.create(
			correo="vet-a@example.com",
			role=self.rol_vet,
			veterinaria=self.vet_a,
			is_active=True,
		)
		Perfil.objects.create(usuario=vet_a_user, nombre="Dra. A")

		vet_b_user = User.objects.create(
			correo="vet-b@example.com",
			role=self.rol_vet,
			veterinaria=self.vet_b,
			is_active=True,
		)
		Perfil.objects.create(usuario=vet_b_user, nombre="Dr. B")

		component = ComponenteSistema.objects.create(
			codigo="CLI_VETERINARIOS",
			nombre="Veterinarios",
			tipo="FORMULARIO",
			modulo="clinica",
			plataforma="WEB",
			estado=True,
		)
		grupo = GrupoUsuario.objects.create(
			nombre="Clinica",
			descripcion="Grupo clinica",
			veterinaria=self.vet_a,
		)
		UsuarioGrupo.objects.create(usuario=self.admin, grupo=grupo)
		GrupoPermisoComponente.objects.create(
			grupo=grupo,
			componente=component,
			puede_ver=True,
			estado=True,
		)

	def test_veterinarios_list_is_tenant_scoped(self):
		self.client.force_login(self.admin)
		response = self.client.get("/api/gestion/clinica/veterinarios/")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["correo"], "vet-a@example.com")

	def test_veterinaria_crud_lifecycle(self):
		self.client.force_login(self.admin)

		create_response = self.client.post(
			"/api/gestion/clinica/veterinarias/",
			{
				"nombre": "Clinica Nueva",
				"slug": "clinica-nueva",
				"nit": "123456",
				"correo": "nuevo@example.com",
				"telefono": "5551234",
				"direccion": "Calle Prueba 123",
				"logo": "logo.png",
				"permite_auto_registro_clientes": True,
			},
			format="json",
		)
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
		veterinaria_id = create_response.data.get("id_veterinaria")
		self.assertIsNotNone(veterinaria_id)
		self.assertEqual(create_response.data.get("slug"), "clinica-nueva")

		detail_response = self.client.get(f"/api/gestion/clinica/veterinarias/{veterinaria_id}/")
		self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
		self.assertEqual(detail_response.data.get("nombre"), "Clinica Nueva")

		patch_response = self.client.patch(
			f"/api/gestion/clinica/veterinarias/{veterinaria_id}/",
			{"telefono": "5554321"},
			format="json",
		)
		self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
		self.assertEqual(patch_response.data.get("telefono"), "5554321")

		delete_response = self.client.delete(f"/api/gestion/clinica/veterinarias/{veterinaria_id}/")
		self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

		list_response = self.client.get("/api/gestion/clinica/veterinarias/")
		self.assertEqual(list_response.status_code, status.HTTP_200_OK)
		self.assertFalse(any(v.get("id_veterinaria") == veterinaria_id for v in list_response.data))

		veterinaria = Veterinaria.objects.filter(id_veterinaria=veterinaria_id).first()
		self.assertIsNotNone(veterinaria)
		self.assertFalse(veterinaria.estado)


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class HistorialClinicoSaaSTests(APITestCase):
	def setUp(self):
		self.vet_a = Veterinaria.objects.create(
			nombre="Vet Historial A",
			slug="vet-historial-a",
			nit="401",
			correo="historial-a@example.com",
		)
		self.vet_b = Veterinaria.objects.create(
			nombre="Vet Historial B",
			slug="vet-historial-b",
			nit="402",
			correo="historial-b@example.com",
		)
		self.rol_admin = Rol.objects.create(nombre=RoleEnum.ADMIN.value, descripcion="Admin")
		self.rol_client = Rol.objects.create(nombre=RoleEnum.CLIENT.value, descripcion="Cliente")

		self.admin_a = User.objects.create(
			correo="admin-hist-a@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=True,
			is_superuser=False,
		)
		self.admin_a.set_password("Admin12345!")
		self.admin_a.save()

		self.client_a = User.objects.create(
			correo="cliente-hist-a@example.com",
			role=self.rol_client,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=False,
			is_superuser=False,
		)
		self.client_b = User.objects.create(
			correo="cliente-hist-b@example.com",
			role=self.rol_client,
			veterinaria=self.vet_b,
			is_active=True,
			is_staff=False,
			is_superuser=False,
		)
		Perfil.objects.create(usuario=self.client_a, nombre="Cliente A")
		Perfil.objects.create(usuario=self.client_b, nombre="Cliente B")

		self.comp_historial = ComponenteSistema.objects.create(
			codigo="CLI_HISTORIALES",
			nombre="Historiales",
			tipo="MODULO",
			modulo="CLINICA",
			plataforma="WEB",
			estado=True,
		)
		self.group_admin_a = GrupoUsuario.objects.create(
			nombre="Grupo Historial A",
			descripcion="Permisos historial A",
			veterinaria=self.vet_a,
		)
		UsuarioGrupo.objects.create(usuario=self.admin_a, grupo=self.group_admin_a, estado=True)
		UsuarioGrupo.objects.create(usuario=self.client_a, grupo=self.group_admin_a, estado=True)
		GrupoPermisoComponente.objects.create(
			grupo=self.group_admin_a,
			componente=self.comp_historial,
			puede_ver=True,
			puede_crear=True,
			estado=True,
		)

		self.especie = Especie.objects.create(nombre="Canino-CU15")
		self.raza = Raza.objects.create(nombre="Mestizo-CU15", especie=self.especie)
		self.mascota_a = Mascota.objects.create(
			usuario=self.client_a,
			especie=self.especie,
			raza=self.raza,
			veterinaria=self.vet_a,
			nombre="Rocky A",
		)
		self.mascota_b = Mascota.objects.create(
			usuario=self.client_b,
			especie=self.especie,
			raza=self.raza,
			veterinaria=self.vet_b,
			nombre="Rocky B",
		)

	def test_historial_por_mascota_creates_once_and_returns_same_record(self):
		self.client.force_login(self.admin_a)
		first = self.client.get(f"/api/gestion/clinica/mascotas/{self.mascota_a.id_mascota}/historial/")
		self.assertEqual(first.status_code, status.HTTP_200_OK)
		first_id = first.data["id_historial_clinico"]

		second = self.client.get(f"/api/gestion/clinica/mascotas/{self.mascota_a.id_mascota}/historial/")
		self.assertEqual(second.status_code, status.HTTP_200_OK)
		self.assertEqual(second.data["id_historial_clinico"], first_id)

	def test_historial_blocks_access_to_other_tenant_pet(self):
		self.client.force_login(self.admin_a)
		response = self.client.get(f"/api/gestion/clinica/mascotas/{self.mascota_b.id_mascota}/historial/")
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_cliente_only_can_access_own_pet_historial(self):
		self.client.force_login(self.client_a)
		own = self.client.get(f"/api/gestion/clinica/mascotas/{self.mascota_a.id_mascota}/historial/")
		self.assertEqual(own.status_code, status.HTTP_200_OK)
		other = self.client.get(f"/api/gestion/clinica/mascotas/{self.mascota_b.id_mascota}/historial/")
		self.assertEqual(other.status_code, status.HTTP_404_NOT_FOUND)
