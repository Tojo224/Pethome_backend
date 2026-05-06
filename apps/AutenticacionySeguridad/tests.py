from datetime import timedelta

from django.db import connection
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models import (
	Bitacora,
	ComponenteSistema,
	GrupoPermisoComponente,
	GrupoUsuario,
	PlanSuscripcion,
	Rol,
	Suscripcion,
	User,
	UsuarioGrupo,
	Veterinaria,
)
from apps.AutenticacionySeguridad.services.bitacora_register_service import BitacoraService

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
		self.plan = PlanSuscripcion.objects.create(
			nombre="Plan Base",
			descripcion="Plan de prueba",
			precio_mensual=100,
			limite_usuarios=10,
			limite_mascotas=100,
			permite_app_movil=True,
			permite_reportes=True,
			permite_backup=False,
			estado=True,
		)
		Suscripcion.objects.create(
			fecha_inicio=timezone.localdate(),
			fecha_fin=timezone.localdate() + timedelta(days=30),
			estado_suscripcion="ACTIVA",
			renovacion_automatica=True,
			veterinaria=self.vet,
			plan=self.plan,
		)
		self.user_tenant = User.objects.create(
			correo="usuario_tenant@example.com",
			role=self.rol_admin,
			veterinaria=self.vet,
			is_active=True,
			is_staff=True,
			is_superuser=False,
		)
		self.user_tenant.set_password("Admin12345!")
		self.user_tenant.save()

	def _login(self, correo=None, password=None):
		return self.client.post(
			"/api/auth/login/",
			{
				"correo": correo or self.user.correo,
				"password": password or "Admin12345!",
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

	def test_login_fails_with_invalid_credentials(self):
		response = self._login(correo=self.user.correo, password="mal-password")
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("detail", response.data)

	def test_login_fails_with_empty_fields(self):
		response = self.client.post(
			"/api/auth/login/",
			{"correo": "", "password": ""},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("correo", response.data)
		self.assertIn("password", response.data)

	def test_login_fails_with_invalid_email_format(self):
		response = self.client.post(
			"/api/auth/login/",
			{"correo": "correo-invalido", "password": "Admin12345!"},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("correo", response.data)

	def test_login_tenant_user_with_active_subscription_is_successful(self):
		response = self._login(correo=self.user_tenant.correo, password="Admin12345!")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("access", response.data)
		self.assertIn("refresh", response.data)
		self.assertEqual(response.data["user"]["correo"], self.user_tenant.correo)
		access_claims = AccessToken(response.data["access"])
		self.assertEqual(access_claims.get("id_usuario"), self.user_tenant.id_usuario)
		self.assertEqual(access_claims.get("id_rol"), self.user_tenant.role_id)
		self.assertEqual(access_claims.get("id_veterinaria"), self.user_tenant.veterinaria_id)
		self.assertEqual(access_claims.get("is_superuser"), self.user_tenant.is_superuser)
		self.assertIn("permisos_base", access_claims)

	def test_login_fails_if_veterinaria_is_inactive(self):
		self.vet.estado = False
		self.vet.save(update_fields=["estado"])
		response = self._login(correo=self.user_tenant.correo, password="Admin12345!")
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("detail", response.data)

	def test_login_movil_fails_if_plan_does_not_allow_mobile(self):
		self.plan.permite_app_movil = False
		self.plan.save(update_fields=["permite_app_movil"])
		response = self.client.post(
			"/api/auth/login/",
			{
				"correo": self.user_tenant.correo,
				"password": "Admin12345!",
				"plataforma": "movil",
			},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("detail", response.data)

	def test_me_returns_authenticated_user_identity(self):
		login_response = self._login(correo=self.user_tenant.correo, password="Admin12345!")
		access_token = login_response.data["access"]
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
		me_response = self.client.get("/api/auth/me/")
		self.assertEqual(me_response.status_code, status.HTTP_200_OK)
		self.assertEqual(me_response.data["correo"], self.user_tenant.correo)

	def test_me_without_auth_returns_unauthorized(self):
		response = self.client.get("/api/auth/me/")
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_me_with_invalid_token_returns_unauthorized(self):
		self.client.credentials(HTTP_AUTHORIZATION="Bearer token-invalido")
		response = self.client.get("/api/auth/me/")
		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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

	def test_logout_token_cannot_be_reused_after_blacklist(self):
		login_response = self._login()
		refresh_token = login_response.data["refresh"]

		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
		first_logout = self.client.post(
			"/api/auth/logout/",
			{"refresh": refresh_token},
			format="json",
		)
		self.assertEqual(first_logout.status_code, status.HTTP_200_OK)

		second_logout = self.client.post(
			"/api/auth/logout/",
			{"refresh": refresh_token},
			format="json",
		)
		self.assertEqual(second_logout.status_code, status.HTTP_400_BAD_REQUEST)

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


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class UsuarioManagementTests(APITestCase):
	def setUp(self):
		self.vet = Veterinaria.objects.create(
			nombre="Vet CU4",
			slug="vet-cu4",
			nit="999",
			correo="vet-cu4@example.com",
		)
		self.plan = PlanSuscripcion.objects.create(
			nombre="Plan CU4",
			descripcion="Plan de prueba CU4",
			precio_mensual=100,
			limite_usuarios=20,
			limite_mascotas=200,
			permite_app_movil=True,
			permite_reportes=True,
			permite_backup=True,
			estado=True,
		)
		Suscripcion.objects.create(
			fecha_inicio=timezone.localdate(),
			fecha_fin=timezone.localdate() + timedelta(days=30),
			estado_suscripcion="ACTIVA",
			renovacion_automatica=True,
			veterinaria=self.vet,
			plan=self.plan,
		)

		self.rol_admin = Rol.objects.create(nombre=RoleEnum.ADMIN.value, descripcion="Admin")
		self.rol_client = Rol.objects.create(nombre=RoleEnum.CLIENT.value, descripcion="Cliente")

		self.component_users = ComponenteSistema.objects.create(
			codigo="SEG_USUARIOS",
			nombre="Gestion usuarios",
			tipo="MODULO",
			modulo="SEGURIDAD",
			ruta="/usuarios",
			plataforma="WEB",
			estado=True,
		)

		self.admin_user = User.objects.create(
			correo="admin-cu4@example.com",
			role=self.rol_admin,
			veterinaria=self.vet,
			is_active=True,
			is_staff=True,
			is_superuser=False,
		)
		self.admin_user.set_password("Admin12345!")
		self.admin_user.save()

		self.normal_user = User.objects.create(
			correo="normal-cu4@example.com",
			role=self.rol_client,
			veterinaria=self.vet,
			is_active=True,
			is_staff=False,
			is_superuser=False,
		)
		self.normal_user.set_password("Admin12345!")
		self.normal_user.save()

		self.admin_group = GrupoUsuario.objects.create(
			nombre="Admins CU4",
			descripcion="Grupo admin para pruebas CU4",
			estado=True,
			veterinaria=self.vet,
		)

		UsuarioGrupo.objects.create(usuario=self.admin_user, grupo=self.admin_group, estado=True)
		GrupoPermisoComponente.objects.create(
			grupo=self.admin_group,
			componente=self.component_users,
			puede_ver=True,
			puede_crear=True,
			puede_editar=True,
			puede_eliminar=True,
			estado=True,
		)

	def _auth_as(self, user):
		login = self.client.post(
			"/api/auth/login/",
			{"correo": user.correo, "password": "Admin12345!"},
			format="json",
		)
		self.assertEqual(login.status_code, status.HTTP_200_OK)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
		return login

	def test_admin_can_list_users(self):
		self._auth_as(self.admin_user)
		response = self.client.get("/api/auth/usuarios/")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("results", response.data)

	def test_admin_can_create_user_and_prevent_duplicate_email(self):
		self._auth_as(self.admin_user)
		payload = {
			"correo": "nuevo-cu4@example.com",
			"password": "Admin12345!",
			"id_rol": self.rol_client.id_rol,
			"nombre": "Nuevo Usuario",
			"telefono": "70000001",
			"direccion": "Zona Centro",
			"estado": True,
		}
		create_response = self.client.post("/api/auth/usuarios/", payload, format="json")
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

		dup_response = self.client.post("/api/auth/usuarios/", payload, format="json")
		self.assertEqual(dup_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("correo", dup_response.data)

	def test_admin_can_update_user(self):
		self._auth_as(self.admin_user)
		target_create = self.client.post(
			"/api/auth/usuarios/",
			{
				"correo": "editar-cu4@example.com",
				"password": "Admin12345!",
				"id_rol": self.rol_client.id_rol,
				"nombre": "Usuario Editar",
				"telefono": "70000002",
				"direccion": "Zona Sur",
				"estado": True,
			},
			format="json",
		)
		self.assertEqual(target_create.status_code, status.HTTP_201_CREATED)
		perfil_id = target_create.data["id_perfil"]

		update_response = self.client.patch(
			f"/api/auth/usuarios/{perfil_id}/",
			{"nombre": "Usuario Editado"},
			format="json",
		)
		self.assertEqual(update_response.status_code, status.HTTP_200_OK)
		self.assertEqual(update_response.data["nombre"], "Usuario Editado")

	def test_admin_can_deactivate_user(self):
		self._auth_as(self.admin_user)
		target_create = self.client.post(
			"/api/auth/usuarios/",
			{
				"correo": "eliminar-cu4@example.com",
				"password": "Admin12345!",
				"id_rol": self.rol_client.id_rol,
				"nombre": "Usuario Eliminar",
				"telefono": "70000003",
				"direccion": "Zona Norte",
				"estado": True,
			},
			format="json",
		)
		self.assertEqual(target_create.status_code, status.HTTP_201_CREATED)
		perfil_id = target_create.data["id_perfil"]
		target_user_id = target_create.data["usuario"]

		delete_response = self.client.delete(f"/api/auth/usuarios/{perfil_id}/")
		self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
		self.assertFalse(User.objects.get(pk=target_user_id).is_active)

	def test_non_admin_without_permission_cannot_manage_users(self):
		self._auth_as(self.normal_user)
		response = self.client.get("/api/auth/usuarios/")
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class RolesPermisosManagementTests(APITestCase):
	def setUp(self):
		self.vet = Veterinaria.objects.create(
			nombre="Vet CU5",
			slug="vet-cu5",
			nit="555",
			correo="vet-cu5@example.com",
		)
		self.other_vet = Veterinaria.objects.create(
			nombre="Vet Externa",
			slug="vet-externa-cu5",
			nit="556",
			correo="vet-externa@example.com",
		)
		self.plan = PlanSuscripcion.objects.create(
			nombre="Plan CU5",
			descripcion="Plan CU5",
			precio_mensual=100,
			limite_usuarios=20,
			limite_mascotas=200,
			permite_app_movil=True,
			permite_reportes=True,
			permite_backup=True,
			estado=True,
		)
		Suscripcion.objects.create(
			fecha_inicio=timezone.localdate(),
			fecha_fin=timezone.localdate() + timedelta(days=30),
			estado_suscripcion="ACTIVA",
			renovacion_automatica=True,
			veterinaria=self.vet,
			plan=self.plan,
		)

		self.rol_admin = Rol.objects.create(nombre=RoleEnum.ADMIN.value, descripcion="Admin")
		self.rol_client = Rol.objects.create(nombre=RoleEnum.CLIENT.value, descripcion="Cliente")

		self.comp_grupo = ComponenteSistema.objects.create(
			codigo="SEG_GRUPO_USUARIO",
			nombre="Gestion Grupos",
			tipo="MODULO",
			modulo="SEGURIDAD",
			ruta="/grupos",
			plataforma="WEB",
			estado=True,
		)
		self.comp_permiso = ComponenteSistema.objects.create(
			codigo="SEG_PERMISO_COMPONENTE",
			nombre="Gestion Permisos",
			tipo="MODULO",
			modulo="SEGURIDAD",
			ruta="/grupos-permisos",
			plataforma="WEB",
			estado=True,
		)
		self.comp_clientes = ComponenteSistema.objects.create(
			codigo="CLI_CLIENTES",
			nombre="Clientes",
			tipo="MODULO",
			modulo="CLIENTES",
			ruta="/clientes",
			plataforma="WEB",
			estado=True,
		)

		self.admin_user = User.objects.create(
			correo="admin-cu5@example.com",
			role=self.rol_admin,
			veterinaria=self.vet,
			is_active=True,
			is_staff=True,
			is_superuser=False,
		)
		self.admin_user.set_password("Admin12345!")
		self.admin_user.save()

		self.normal_user = User.objects.create(
			correo="normal-cu5@example.com",
			role=self.rol_client,
			veterinaria=self.vet,
			is_active=True,
			is_staff=False,
			is_superuser=False,
		)
		self.normal_user.set_password("Admin12345!")
		self.normal_user.save()

		self.security_group = GrupoUsuario.objects.create(
			nombre="Seguridad CU5",
			descripcion="Grupo con permisos CU5",
			estado=True,
			veterinaria=self.vet,
		)
		UsuarioGrupo.objects.create(usuario=self.admin_user, grupo=self.security_group, estado=True)
		GrupoPermisoComponente.objects.create(
			grupo=self.security_group,
			componente=self.comp_grupo,
			puede_ver=True,
			puede_crear=True,
			puede_editar=True,
			puede_eliminar=True,
			estado=True,
		)
		GrupoPermisoComponente.objects.create(
			grupo=self.security_group,
			componente=self.comp_permiso,
			puede_ver=True,
			puede_crear=True,
			puede_editar=True,
			puede_eliminar=True,
			estado=True,
		)

		self.foreign_group = GrupoUsuario.objects.create(
			nombre="Grupo Externo",
			descripcion="No debería ser visible",
			estado=True,
			veterinaria=self.other_vet,
		)

	def _auth_as(self, user):
		login = self.client.post(
			"/api/auth/login/",
			{"correo": user.correo, "password": "Admin12345!"},
			format="json",
		)
		self.assertEqual(login.status_code, status.HTTP_200_OK)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

	def test_admin_can_manage_grupos_and_is_tenant_scoped(self):
		self._auth_as(self.admin_user)
		list_response = self.client.get("/api/auth/grupos/")
		self.assertEqual(list_response.status_code, status.HTTP_200_OK)
		self.assertTrue(all(item["id_veterinaria"] == self.vet.id_veterinaria for item in list_response.data))

		create_response = self.client.post(
			"/api/auth/grupos/",
			{"nombre": "Recepcion CU5", "descripcion": "Recepción", "estado": True},
			format="json",
		)
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
		grupo_id = create_response.data["id_grupo"]

		patch_response = self.client.patch(
			f"/api/auth/grupos/{grupo_id}/",
			{"descripcion": "Recepción Editada"},
			format="json",
		)
		self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
		self.assertEqual(patch_response.data["descripcion"], "Recepción Editada")

		foreign_access = self.client.get(f"/api/auth/grupos/{self.foreign_group.id_grupo}/")
		self.assertEqual(foreign_access.status_code, status.HTTP_404_NOT_FOUND)

		delete_response = self.client.delete(f"/api/auth/grupos/{grupo_id}/")
		self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

	def test_admin_can_assign_edit_remove_permiso_por_componente(self):
		self._auth_as(self.admin_user)
		target_group = GrupoUsuario.objects.create(
			nombre="Veterinarios CU5",
			descripcion="Grupo veterinarios",
			estado=True,
			veterinaria=self.vet,
		)
		create_permiso = self.client.post(
			"/api/auth/grupos-permisos/",
			{
				"grupo": target_group.id_grupo,
				"componente": self.comp_clientes.id_componente,
				"puede_ver": True,
				"puede_crear": False,
				"puede_editar": False,
				"puede_eliminar": False,
				"puede_exportar": False,
				"puede_ejecutar": False,
				"estado": True,
			},
			format="json",
		)
		self.assertEqual(create_permiso.status_code, status.HTTP_201_CREATED)
		permiso_id = create_permiso.data["id_permiso_componente"]

		edit_permiso = self.client.patch(
			f"/api/auth/grupos-permisos/{permiso_id}/",
			{"puede_crear": True, "puede_editar": True},
			format="json",
		)
		self.assertEqual(edit_permiso.status_code, status.HTTP_200_OK)
		self.assertTrue(edit_permiso.data["puede_crear"])
		self.assertTrue(edit_permiso.data["puede_editar"])

		remove_permiso = self.client.delete(f"/api/auth/grupos-permisos/{permiso_id}/")
		self.assertEqual(remove_permiso.status_code, status.HTTP_204_NO_CONTENT)

	def test_non_admin_without_permissions_cannot_manage_roles_and_permisos(self):
		self._auth_as(self.normal_user)
		response_grupos = self.client.get("/api/auth/grupos/")
		self.assertEqual(response_grupos.status_code, status.HTTP_403_FORBIDDEN)
		response_permisos = self.client.get("/api/auth/grupos-permisos/")
		self.assertEqual(response_permisos.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class BitacoraSaaSTests(APITestCase):
	def setUp(self):
		self.vet_a = Veterinaria.objects.create(
			nombre="Vet CU6 A",
			slug="vet-cu6-a",
			nit="661",
			correo="vet-cu6-a@example.com",
		)
		self.vet_b = Veterinaria.objects.create(
			nombre="Vet CU6 B",
			slug="vet-cu6-b",
			nit="662",
			correo="vet-cu6-b@example.com",
		)
		self.plan = PlanSuscripcion.objects.create(
			nombre="Plan CU6",
			descripcion="Plan CU6",
			precio_mensual=100,
			limite_usuarios=20,
			limite_mascotas=200,
			permite_app_movil=True,
			permite_reportes=True,
			permite_backup=True,
			estado=True,
		)
		Suscripcion.objects.create(
			fecha_inicio=timezone.localdate(),
			fecha_fin=timezone.localdate() + timedelta(days=30),
			estado_suscripcion="ACTIVA",
			renovacion_automatica=True,
			veterinaria=self.vet_a,
			plan=self.plan,
		)
		Suscripcion.objects.create(
			fecha_inicio=timezone.localdate(),
			fecha_fin=timezone.localdate() + timedelta(days=30),
			estado_suscripcion="ACTIVA",
			renovacion_automatica=True,
			veterinaria=self.vet_b,
			plan=self.plan,
		)

		self.rol_admin = Rol.objects.create(nombre=RoleEnum.ADMIN.value, descripcion="Admin")
		self.comp_bitacora = ComponenteSistema.objects.create(
			codigo="SEG_BITACORA",
			nombre="Bitacora",
			tipo="MODULO",
			modulo="SEGURIDAD",
			ruta="/bitacora",
			plataforma="WEB",
			estado=True,
		)

		self.admin_a = User.objects.create(
			correo="admin-cu6-a@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=True,
			is_superuser=False,
		)
		self.admin_a.set_password("Admin12345!")
		self.admin_a.save()

		self.superadmin = User.objects.create(
			correo="super-cu6@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=True,
			is_superuser=True,
		)
		self.superadmin.set_password("Admin12345!")
		self.superadmin.save()

		self.group_a = GrupoUsuario.objects.create(
			nombre="Seguridad CU6 A",
			descripcion="Permiso bitacora vet A",
			estado=True,
			veterinaria=self.vet_a,
		)
		UsuarioGrupo.objects.create(usuario=self.admin_a, grupo=self.group_a, estado=True)
		GrupoPermisoComponente.objects.create(
			grupo=self.group_a,
			componente=self.comp_bitacora,
			puede_ver=True,
			estado=True,
		)

		BitacoraService.registrar_evento(
			accion="CU6_EVENTO_A",
			descripcion="Evento vet A",
			usuario=self.admin_a,
			modulo="bitacora",
			resultado="EXITO",
		)
		admin_b = User.objects.create(
			correo="admin-cu6-b@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_b,
			is_active=True,
			is_staff=True,
			is_superuser=False,
		)
		admin_b.set_password("Admin12345!")
		admin_b.save()
		BitacoraService.registrar_evento(
			accion="CU6_EVENTO_B",
			descripcion="Evento vet B",
			usuario=admin_b,
			modulo="bitacora",
			resultado="EXITO",
		)
		BitacoraService.registrar_evento(
			accion="CU6_EVENTO_GLOBAL",
			descripcion="Evento global superadmin",
			usuario=self.superadmin,
			modulo="bitacora",
			resultado="EXITO",
		)

	def _auth_as(self, user):
		login = self.client.post(
			"/api/auth/login/",
			{"correo": user.correo, "password": "Admin12345!"},
			format="json",
		)
		self.assertEqual(login.status_code, status.HTTP_200_OK)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

	def test_admin_only_sees_bitacora_of_own_veterinaria(self):
		self._auth_as(self.admin_a)
		response = self.client.get("/api/auth/bitacora/")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		results = response.data.get("results", [])
		self.assertGreaterEqual(len(results), 1)
		acciones = {item.get("accion") for item in results}
		self.assertIn("CU6_EVENTO_A", acciones)
		self.assertNotIn("CU6_EVENTO_B", acciones)

	def test_superadmin_can_see_global_and_tenant_bitacora(self):
		self._auth_as(self.superadmin)
		response = self.client.get("/api/auth/bitacora/")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		results = response.data.get("results", [])
		acciones = {item.get("accion") for item in results}
		self.assertIn("CU6_EVENTO_A", acciones)
		self.assertIn("CU6_EVENTO_B", acciones)
		self.assertIn("CU6_EVENTO_GLOBAL", acciones)
