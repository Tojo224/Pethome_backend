from datetime import time, timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models import (
	ComponenteSistema,
	GrupoPermisoComponente,
	GrupoUsuario,
	Rol,
	User,
	UsuarioGrupo,
	Veterinaria,
)
from apps.GestionClientesyMascotas.models import Especie, Mascota, Raza
from apps.GestionServiciosyReserva.models import (
	CategoriaServicio,
	PrecioServicio,
	Servicio,
)

FERNET_TEST_KEY = "y-8vRXvZL5t7I8S_dZd2a0B7aKXzH_kL8BkpE9SLiW8="


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class CitasRBACTests(APITestCase):
	def setUp(self):
		self.vet = Veterinaria.objects.create(
			nombre="Vet Servicios",
			slug="vet-servicios",
			nit="900",
			correo="servicios@example.com",
		)
		self.rol_admin = Rol.objects.create(
			nombre=RoleEnum.ADMIN.value,
			descripcion="Administrador",
		)
		self.rol_client = Rol.objects.create(
			nombre=RoleEnum.CLIENT.value,
			descripcion="Cliente",
		)

		self.user = User.objects.create(
			correo="admin-servicios@example.com",
			role=self.rol_admin,
			veterinaria=self.vet,
			is_active=True,
			is_staff=True,
			is_superuser=False,
		)
		self.user.set_password("Admin12345!")
		self.user.save()

		self.client_user = User.objects.create(
			correo="cliente-servicios@example.com",
			role=self.rol_client,
			veterinaria=self.vet,
			is_active=True,
			is_staff=False,
			is_superuser=False,
		)

		self.component = ComponenteSistema.objects.create(
			codigo="SERV_CITAS",
			nombre="Citas",
			tipo="FORMULARIO",
			modulo="servicios",
			plataforma="WEB",
			estado=True,
		)

		self.grupo = GrupoUsuario.objects.create(
			nombre="Recepcionistas",
			descripcion="Grupo de prueba",
			veterinaria=self.vet,
		)
		UsuarioGrupo.objects.create(usuario=self.user, grupo=self.grupo)

		self.especie = Especie.objects.create(nombre="Canino")
		self.raza = Raza.objects.create(nombre="Labrador", especie=self.especie)
		self.mascota = Mascota.objects.create(
			usuario=self.client_user,
			especie=self.especie,
			raza=self.raza,
			veterinaria=self.vet,
			nombre="Firulais",
		)
		self.categoria = CategoriaServicio.objects.create(
			nombre="Consulta",
			descripcion="General",
			veterinaria=self.vet,
		)
		self.servicio = Servicio.objects.create(
			nombre="Consulta General",
			descripcion="General",
			categoria=self.categoria,
			duracion_estimada=30,
			disponible_domicilio=True,
			veterinaria=self.vet,
		)
		self.precio = PrecioServicio.objects.create(
			servicio=self.servicio,
			variacion="General",
			modalidad="CLINICA",
			precio=50,
			descripcion="Precio base",
			veterinaria=self.vet,
		)

	def _grant_permissions(self, *, puede_ver=False, puede_crear=False):
		GrupoPermisoComponente.objects.create(
			grupo=self.grupo,
			componente=self.component,
			puede_ver=puede_ver,
			puede_crear=puede_crear,
			puede_editar=False,
			puede_eliminar=False,
			estado=True,
		)

	def test_citas_view_only_denies_create(self):
		self._grant_permissions(puede_ver=True, puede_crear=False)
		self.client.force_login(self.user)

		list_response = self.client.get("/api/gestion/servicios/citas/")
		self.assertEqual(list_response.status_code, status.HTTP_200_OK)

		create_response = self.client.post("/api/gestion/servicios/citas/", {}, format="json")
		self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

	def test_citas_create_allowed_with_permission(self):
		self._grant_permissions(puede_ver=True, puede_crear=True)
		self.client.force_login(self.user)

		payload = {
			"mascota": self.mascota.id_mascota,
			"servicio": self.servicio.id_servicio,
			"precio_servicio": self.precio.id_precio,
			"fecha_programada": (timezone.localdate() + timedelta(days=1)).isoformat(),
			"hora_inicio": time(10, 0).isoformat(),
			"modalidad": "CLINICA",
			"descripcion": "Consulta de rutina",
		}

		response = self.client.post(
			"/api/gestion/servicios/citas/",
			payload,
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class CatalogoServiciosSaaSTests(APITestCase):
	def setUp(self):
		self.vet_a = Veterinaria.objects.create(
			nombre="Vet Catalogo A",
			slug="vet-catalogo-a",
			nit="901",
			correo="catalogo-a@example.com",
		)
		self.vet_b = Veterinaria.objects.create(
			nombre="Vet Catalogo B",
			slug="vet-catalogo-b",
			nit="902",
			correo="catalogo-b@example.com",
		)
		self.rol_admin = Rol.objects.create(
			nombre=RoleEnum.ADMIN.value,
			descripcion="Administrador",
		)
		self.admin_a = User.objects.create(
			correo="admin-catalogo-a@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=True,
			is_superuser=True,
		)
		self.admin_a.set_password("Admin12345!")
		self.admin_a.save()

		self.comp_cat = ComponenteSistema.objects.create(
			codigo="SERV_CATEGORIAS",
			nombre="Categorias",
			tipo="MODULO",
			modulo="SERVICIOS",
			plataforma="WEB",
			estado=True,
		)
		self.comp_srv = ComponenteSistema.objects.create(
			codigo="SERV_SERVICIOS",
			nombre="Servicios",
			tipo="MODULO",
			modulo="SERVICIOS",
			plataforma="WEB",
			estado=True,
		)
		self.comp_pre = ComponenteSistema.objects.create(
			codigo="SERV_PRECIOS",
			nombre="Precios",
			tipo="MODULO",
			modulo="SERVICIOS",
			plataforma="WEB",
			estado=True,
		)
		self.group = GrupoUsuario.objects.create(
			nombre="Catalogo Admin",
			descripcion="Permisos catálogo",
			veterinaria=self.vet_a,
		)
		UsuarioGrupo.objects.create(usuario=self.admin_a, grupo=self.group)
		for comp in [self.comp_cat, self.comp_srv, self.comp_pre]:
			GrupoPermisoComponente.objects.create(
				grupo=self.group,
				componente=comp,
				puede_ver=True,
				puede_crear=True,
				puede_editar=True,
				puede_eliminar=True,
				estado=True,
			)

		self.cat_b = CategoriaServicio.objects.create(
			nombre="Categoria B",
			descripcion="Otra vet",
			veterinaria=self.vet_b,
		)
		self.serv_b = Servicio.objects.create(
			nombre="Servicio B",
			descripcion="Otra vet",
			categoria=self.cat_b,
			duracion_estimada=30,
			disponible_domicilio=True,
			veterinaria=self.vet_b,
		)

	def test_catalogo_is_tenant_scoped_and_price_validation_works(self):
		self.client.force_login(self.admin_a)

		cat_create = self.client.post(
			"/api/gestion/servicios/categorias-servicio/",
			{"nombre": "Consulta", "descripcion": "General", "estado": True},
			format="json",
		)
		self.assertEqual(cat_create.status_code, status.HTTP_201_CREATED)
		cat_id = cat_create.data["id_categoria"]

		srv_create = self.client.post(
			"/api/gestion/servicios/",
			{
				"nombre": "Consulta General",
				"descripcion": "Atencion basica",
				"categoria": cat_id,
				"duracion_estimada": 30,
				"disponible_domicilio": True,
				"estado": True,
			},
			format="json",
		)
		self.assertEqual(srv_create.status_code, status.HTTP_201_CREATED)
		srv_id = srv_create.data["id_servicio"]

		list_cat = self.client.get("/api/gestion/servicios/categorias-servicio/")
		self.assertEqual(list_cat.status_code, status.HTTP_200_OK)
		self.assertTrue(all(c["id_categoria"] != self.cat_b.id_categoria for c in list_cat.data))

		list_srv = self.client.get("/api/gestion/servicios/")
		self.assertEqual(list_srv.status_code, status.HTTP_200_OK)
		self.assertTrue(all(s["id_servicio"] != self.serv_b.id_servicio for s in list_srv.data))

		price_invalid = self.client.post(
			"/api/gestion/servicios/precios-servicio/",
			{
				"servicio": srv_id,
				"variacion": "Base",
				"modalidad": "CLINICA",
				"precio": 0,
				"descripcion": "Invalido",
				"estado": True,
			},
			format="json",
		)
		self.assertEqual(price_invalid.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("precio", price_invalid.data)


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class CitasAgendaSaaSTests(APITestCase):
	def setUp(self):
		self.vet_a = Veterinaria.objects.create(
			nombre="Vet Agenda A",
			slug="vet-agenda-a",
			nit="903",
			correo="agenda-a@example.com",
		)
		self.vet_b = Veterinaria.objects.create(
			nombre="Vet Agenda B",
			slug="vet-agenda-b",
			nit="904",
			correo="agenda-b@example.com",
		)
		self.rol_admin = Rol.objects.create(nombre=RoleEnum.ADMIN.value, descripcion="Admin")
		self.rol_client = Rol.objects.create(nombre=RoleEnum.CLIENT.value, descripcion="Cliente")

		self.admin_a = User.objects.create(
			correo="admin-agenda-a@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=True,
			is_superuser=True,
		)
		self.admin_a.set_password("Admin12345!")
		self.admin_a.save()

		self.client_a = User.objects.create(
			correo="cliente-agenda-a@example.com",
			role=self.rol_client,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=False,
			is_superuser=False,
		)
		self.client_b = User.objects.create(
			correo="cliente-agenda-b@example.com",
			role=self.rol_client,
			veterinaria=self.vet_b,
			is_active=True,
			is_staff=False,
			is_superuser=False,
		)

		self.comp_citas = ComponenteSistema.objects.create(
			codigo="SERV_CITAS",
			nombre="Citas",
			tipo="MODULO",
			modulo="SERVICIOS",
			plataforma="WEB",
			estado=True,
		)
		self.grp_admin_a = GrupoUsuario.objects.create(
			nombre="Agenda Admin A",
			descripcion="Permisos agenda admin A",
			veterinaria=self.vet_a,
		)
		UsuarioGrupo.objects.create(usuario=self.admin_a, grupo=self.grp_admin_a)
		GrupoPermisoComponente.objects.create(
			grupo=self.grp_admin_a,
			componente=self.comp_citas,
			puede_ver=True,
			puede_crear=True,
			puede_editar=True,
			puede_eliminar=True,
			estado=True,
		)
		self.grp_client_a = GrupoUsuario.objects.create(
			nombre="Agenda Cliente A",
			descripcion="Permisos agenda cliente A",
			veterinaria=self.vet_a,
		)
		UsuarioGrupo.objects.create(usuario=self.client_a, grupo=self.grp_client_a)
		GrupoPermisoComponente.objects.create(
			grupo=self.grp_client_a,
			componente=self.comp_citas,
			puede_ver=True,
			puede_crear=True,
			estado=True,
		)

		self.especie = Especie.objects.create(nombre="Felino")
		self.raza = Raza.objects.create(nombre="Siames", especie=self.especie)
		self.mascota_a = Mascota.objects.create(
			usuario=self.client_a,
			especie=self.especie,
			raza=self.raza,
			veterinaria=self.vet_a,
			nombre="Mishi A",
		)
		self.mascota_b = Mascota.objects.create(
			usuario=self.client_b,
			especie=self.especie,
			raza=self.raza,
			veterinaria=self.vet_b,
			nombre="Mishi B",
		)
		self.cat_a = CategoriaServicio.objects.create(
			nombre="Consulta Agenda A",
			descripcion="Consulta",
			veterinaria=self.vet_a,
		)
		self.cat_b = CategoriaServicio.objects.create(
			nombre="Consulta Agenda B",
			descripcion="Consulta",
			veterinaria=self.vet_b,
		)
		self.serv_a = Servicio.objects.create(
			nombre="Servicio Agenda A",
			descripcion="Servicio A",
			categoria=self.cat_a,
			duracion_estimada=30,
			disponible_domicilio=True,
			veterinaria=self.vet_a,
		)
		self.serv_b = Servicio.objects.create(
			nombre="Servicio Agenda B",
			descripcion="Servicio B",
			categoria=self.cat_b,
			duracion_estimada=30,
			disponible_domicilio=True,
			veterinaria=self.vet_b,
		)
		self.precio_a = PrecioServicio.objects.create(
			servicio=self.serv_a,
			variacion="Base A",
			modalidad="CLINICA",
			precio=80,
			descripcion="Precio A",
			veterinaria=self.vet_a,
		)
		self.precio_b = PrecioServicio.objects.create(
			servicio=self.serv_b,
			variacion="Base B",
			modalidad="CLINICA",
			precio=90,
			descripcion="Precio B",
			veterinaria=self.vet_b,
		)

	def _future_date(self):
		return (timezone.localdate() + timedelta(days=1)).isoformat()

	def test_cu11_cliente_cannot_request_cita_for_other_tenant_mascota(self):
		self.client.force_login(self.client_a)
		response = self.client.post(
			"/api/gestion/servicios/citas/",
			{
				"mascota": self.mascota_b.id_mascota,
				"servicio": self.serv_a.id_servicio,
				"precio_servicio": self.precio_a.id_precio,
				"fecha_programada": self._future_date(),
				"hora_inicio": "10:00:00",
				"modalidad": "CLINICA",
			},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_cu11_cliente_cannot_use_service_from_other_tenant(self):
		self.client.force_login(self.client_a)
		response = self.client.post(
			"/api/gestion/servicios/citas/",
			{
				"mascota": self.mascota_a.id_mascota,
				"servicio": self.serv_b.id_servicio,
				"precio_servicio": self.precio_b.id_precio,
				"fecha_programada": self._future_date(),
				"hora_inicio": "11:00:00",
				"modalidad": "CLINICA",
			},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_cu12_admin_can_create_and_cancel_reserva(self):
		self.client.force_login(self.admin_a)
		create = self.client.post(
			"/api/gestion/servicios/citas/",
			{
				"mascota": self.mascota_a.id_mascota,
				"servicio": self.serv_a.id_servicio,
				"precio_servicio": self.precio_a.id_precio,
				"fecha_programada": self._future_date(),
				"hora_inicio": "12:00:00",
				"modalidad": "CLINICA",
			},
			format="json",
		)
		self.assertEqual(create.status_code, status.HTTP_201_CREATED)
		cita_id = create.data["id_cita"]

		cancel = self.client.delete(f"/api/gestion/servicios/citas/{cita_id}/")
		self.assertEqual(cancel.status_code, status.HTTP_200_OK)
		self.assertEqual(cancel.data["estado"], "CANCELADA")

	def test_cu13_disponibilidad_and_conflicto_are_tenant_scoped(self):
		self.client.force_login(self.admin_a)
		create = self.client.post(
			"/api/gestion/servicios/citas/",
			{
				"mascota": self.mascota_a.id_mascota,
				"servicio": self.serv_a.id_servicio,
				"precio_servicio": self.precio_a.id_precio,
				"fecha_programada": self._future_date(),
				"hora_inicio": "13:00:00",
				"modalidad": "CLINICA",
			},
			format="json",
		)
		self.assertEqual(create.status_code, status.HTTP_201_CREATED)

		agenda = self.client.get(f"/api/gestion/servicios/agenda/?fecha={self._future_date()}")
		self.assertEqual(agenda.status_code, status.HTTP_200_OK)
		self.assertGreaterEqual(len(agenda.data["citas_ocupadas"]), 1)

		conflict = self.client.get(
			f"/api/gestion/servicios/agenda/validar/?fecha={self._future_date()}&hora_inicio=13:00:00&hora_fin=13:30:00"
		)
		self.assertEqual(conflict.status_code, status.HTTP_200_OK)
		self.assertFalse(conflict.data["disponible"])
