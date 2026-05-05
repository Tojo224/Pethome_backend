from django.test import override_settings
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
from apps.GestionInventarioProveedores.models import CategoriaProducto, Producto, Proveedor

FERNET_TEST_KEY = "y-8vRXvZL5t7I8S_dZd2a0B7aKXzH_kL8BkpE9SLiW8="


@override_settings(BITACORA_SECRET_KEYS=[FERNET_TEST_KEY])
class ProductoTenantTests(APITestCase):
	def setUp(self):
		self.vet_a = Veterinaria.objects.create(
			nombre="Vet Inventario A",
			slug="vet-inv-a",
			nit="101",
			correo="inv-a@example.com",
		)
		self.vet_b = Veterinaria.objects.create(
			nombre="Vet Inventario B",
			slug="vet-inv-b",
			nit="202",
			correo="inv-b@example.com",
		)

		self.rol_admin = Rol.objects.create(
			nombre=RoleEnum.ADMIN.value,
			descripcion="Administrador",
		)

		self.user = User.objects.create(
			correo="inventario@example.com",
			role=self.rol_admin,
			veterinaria=self.vet_a,
			is_active=True,
			is_staff=True,
			is_superuser=False,
		)
		self.user.set_password("Admin12345!")
		self.user.save()

		self.component = ComponenteSistema.objects.create(
			codigo="INV_PRODUCTOS",
			nombre="Productos",
			tipo="FORMULARIO",
			modulo="inventario",
			plataforma="WEB",
			estado=True,
		)
		self.grupo = GrupoUsuario.objects.create(
			nombre="Inventario",
			descripcion="Grupo inventario",
			veterinaria=self.vet_a,
		)
		UsuarioGrupo.objects.create(usuario=self.user, grupo=self.grupo)
		GrupoPermisoComponente.objects.create(
			grupo=self.grupo,
			componente=self.component,
			puede_ver=True,
			estado=True,
		)

		categoria_a = CategoriaProducto.objects.create(
			nombre="Medicamentos",
			veterinaria=self.vet_a,
		)
		proveedor_a = Proveedor.objects.create(
			nombre="Proveedor A",
			veterinaria=self.vet_a,
		)
		Producto.objects.create(
			categoria_producto=categoria_a,
			proveedor=proveedor_a,
			nombre="Antiparasitario",
			precio_compra=10,
			precio_venta=15,
			veterinaria=self.vet_a,
		)

		categoria_b = CategoriaProducto.objects.create(
			nombre="Accesorios",
			veterinaria=self.vet_b,
		)
		proveedor_b = Proveedor.objects.create(
			nombre="Proveedor B",
			veterinaria=self.vet_b,
		)
		Producto.objects.create(
			categoria_producto=categoria_b,
			proveedor=proveedor_b,
			nombre="Collar",
			precio_compra=5,
			precio_venta=8,
			veterinaria=self.vet_b,
		)

	def test_productos_list_is_tenant_scoped(self):
		self.client.force_login(self.user)
		response = self.client.get("/api/gestion/inventario/productos/")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["nombre"], "Antiparasitario")
