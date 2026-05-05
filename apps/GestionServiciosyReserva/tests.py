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