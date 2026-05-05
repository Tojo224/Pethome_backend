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
