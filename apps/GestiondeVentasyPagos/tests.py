from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.AutenticacionySeguridad.enums.roles import RoleEnum
from apps.AutenticacionySeguridad.models import Rol, User, Veterinaria
from apps.GestionClientesyMascotas.models import Mascota
from apps.GestionInventarioProveedores.models import (
    CategoriaProducto,
    MovimientoInventario,
    Producto,
    PuntoInventario,
    StockPunto,
)
from apps.GestionServiciosyReserva.models import CategoriaServicio, Especie, PrecioServicio, Raza, Servicio
from apps.GestiondeVentasyPagos.models import Venta
from apps.NotificacionesySeguimiento.models import Pedido


class CarritoTemporalMobileTests(APITestCase):
    def setUp(self):
        self.vet_a = Veterinaria.objects.create(
            nombre="Vet Carrito A",
            slug="vet-carrito-a",
            correo="vet-carrito-a@example.com",
        )
        self.vet_b = Veterinaria.objects.create(
            nombre="Vet Carrito B",
            slug="vet-carrito-b",
            correo="vet-carrito-b@example.com",
        )

        self.rol_client = Rol.objects.create(nombre=RoleEnum.CLIENT.value, descripcion="Cliente")
        self.rol_admin = Rol.objects.create(nombre=RoleEnum.ADMIN.value, descripcion="Admin")

        self.client_a = User.objects.create(
            correo="cliente-a-carrito@example.com",
            role=self.rol_client,
            veterinaria=self.vet_a,
            is_active=True,
        )
        self.client_same_tenant_other = User.objects.create(
            correo="cliente-otro-carrito@example.com",
            role=self.rol_client,
            veterinaria=self.vet_a,
            is_active=True,
        )
        self.client_b = User.objects.create(
            correo="cliente-b-carrito@example.com",
            role=self.rol_client,
            veterinaria=self.vet_b,
            is_active=True,
        )
        self.admin_a = User.objects.create(
            correo="admin-a-carrito@example.com",
            role=self.rol_admin,
            veterinaria=self.vet_a,
            is_active=True,
            is_staff=True,
        )

        self.cat_producto_a = CategoriaProducto.objects.create(
            nombre="Alimentos A",
            veterinaria=self.vet_a,
            estado=True,
        )
        self.cat_producto_b = CategoriaProducto.objects.create(
            nombre="Alimentos B",
            veterinaria=self.vet_b,
            estado=True,
        )
        self.producto_a = Producto.objects.create(
            categoria_producto=self.cat_producto_a,
            nombre="Alimento premium A",
            precio_venta=Decimal("50.00"),
            visible_catalogo=True,
            estado=True,
            veterinaria=self.vet_a,
        )
        self.producto_b = Producto.objects.create(
            categoria_producto=self.cat_producto_b,
            nombre="Alimento premium B",
            precio_venta=Decimal("35.00"),
            visible_catalogo=True,
            estado=True,
            veterinaria=self.vet_b,
        )
        self.punto_a = PuntoInventario.objects.create(
            veterinaria=self.vet_a,
            tipo=PuntoInventario.TipoPunto.ALMACEN_GENERAL,
            nombre="Almacen Central A",
            estado=True,
        )
        StockPunto.objects.create(
            punto_inventario=self.punto_a,
            producto=self.producto_a,
            veterinaria=self.vet_a,
            cantidad=Decimal("10.00"),
            cantidad_minima=Decimal("1.00"),
        )

        self.cat_servicio_a = CategoriaServicio.objects.create(
            nombre="Higiene A",
            descripcion="Servicios higiene A",
            veterinaria=self.vet_a,
            estado=True,
        )
        self.cat_servicio_b = CategoriaServicio.objects.create(
            nombre="Higiene B",
            descripcion="Servicios higiene B",
            veterinaria=self.vet_b,
            estado=True,
        )
        self.servicio_a = Servicio.objects.create(
            nombre="Baño A",
            descripcion="Baño para mascotas A",
            categoria=self.cat_servicio_a,
            estado=True,
            veterinaria=self.vet_a,
        )
        self.servicio_b = Servicio.objects.create(
            nombre="Baño B",
            descripcion="Baño para mascotas B",
            categoria=self.cat_servicio_b,
            estado=True,
            veterinaria=self.vet_b,
        )
        self.precio_servicio_a = PrecioServicio.objects.create(
            servicio=self.servicio_a,
            variacion="General",
            modalidad="Clinica",
            precio=Decimal("80.00"),
            estado=True,
            veterinaria=self.vet_a,
        )
        self.precio_servicio_b = PrecioServicio.objects.create(
            servicio=self.servicio_b,
            variacion="General",
            modalidad="Clinica",
            precio=Decimal("90.00"),
            estado=True,
            veterinaria=self.vet_b,
        )

        self.especie = Especie.objects.create(nombre="Canino Carrito")
        self.raza = Raza.objects.create(nombre="Mestizo Carrito", especie=self.especie)
        self.mascota_a = Mascota.objects.create(
            usuario=self.client_a,
            especie=self.especie,
            raza=self.raza,
            veterinaria=self.vet_a,
            nombre="Firulais",
            fecha_nac=date(2023, 1, 1),
            estado=True,
        )
        self.mascota_otra_persona = Mascota.objects.create(
            usuario=self.client_same_tenant_other,
            especie=self.especie,
            raza=self.raza,
            veterinaria=self.vet_a,
            nombre="Luna",
            fecha_nac=date(2023, 2, 1),
            estado=True,
        )

    def test_cliente_obtiene_carrito_vacio(self):
        self.client.force_login(self.client_a)
        response = self.client.get("/api/gestion/ventas-pagos/carrito/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_carrito"], "ACTIVO")
        self.assertEqual(response.data["detalles"], [])
        self.assertEqual(Decimal(response.data["subtotal_estimado"]), Decimal("0"))
        self.assertEqual(Decimal(response.data["total_estimado"]), Decimal("0"))

    def test_agregar_producto_no_crea_venta_pedido_pago_ni_movimiento(self):
        self.client.force_login(self.client_a)
        ventas_antes = Venta.objects.count()
        pedidos_antes = Pedido.objects.count()
        movimientos_antes = MovimientoInventario.objects.count()
        stock_antes = StockPunto.objects.get(producto=self.producto_a, veterinaria=self.vet_a).cantidad

        response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto_a.id_producto,
                "cantidad": "2",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["detalles"]), 1)
        self.assertEqual(response.data["detalles"][0]["tipo_item"], "PRODUCTO")
        self.assertEqual(Decimal(response.data["total_estimado"]), Decimal("100.00"))

        self.assertEqual(Venta.objects.count(), ventas_antes)
        self.assertEqual(Pedido.objects.count(), pedidos_antes)
        self.assertEqual(MovimientoInventario.objects.count(), movimientos_antes)

        stock_despues = StockPunto.objects.get(producto=self.producto_a, veterinaria=self.vet_a).cantidad
        self.assertEqual(stock_despues, stock_antes)

    def test_agregar_servicio_sin_mascota_devuelve_error(self):
        self.client.force_login(self.client_a)
        response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "SERVICIO",
                "servicio": self.servicio_a.id_servicio,
                "precio_servicio": self.precio_servicio_a.id_precio,
                "cantidad": "1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("mascota", str(response.data).lower())

    def test_agregar_producto_de_otra_veterinaria_devuelve_error(self):
        self.client.force_login(self.client_a)
        response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto_b.id_producto,
                "cantidad": "1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("veterinaria", str(response.data).lower())

    def test_mascota_de_otro_cliente_en_servicio_devuelve_error(self):
        self.client.force_login(self.client_a)
        response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "SERVICIO",
                "servicio": self.servicio_a.id_servicio,
                "precio_servicio": self.precio_servicio_a.id_precio,
                "mascota": self.mascota_otra_persona.id_mascota,
                "cantidad": "1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente autenticado", str(response.data).lower())

    def test_actualizar_cantidad_recalcula_totales(self):
        self.client.force_login(self.client_a)
        add_response = self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto_a.id_producto,
                "cantidad": "1",
            },
            format="json",
        )
        detalle_id = add_response.data["detalles"][0]["id_detalle_carrito"]

        update_response = self.client.patch(
            f"/api/gestion/ventas-pagos/carrito/items/{detalle_id}/",
            {"cantidad": "3"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(update_response.data["total_estimado"]), Decimal("150.00"))
        self.assertEqual(Decimal(update_response.data["detalles"][0]["subtotal_estimado"]), Decimal("150.00"))

    def test_vaciar_carrito_deja_total_en_cero(self):
        self.client.force_login(self.client_a)
        self.client.post(
            "/api/gestion/ventas-pagos/carrito/items/",
            {
                "tipo_item": "PRODUCTO",
                "producto": self.producto_a.id_producto,
                "cantidad": "2",
            },
            format="json",
        )

        vaciar_response = self.client.delete("/api/gestion/ventas-pagos/carrito/vaciar/")
        self.assertEqual(vaciar_response.status_code, status.HTTP_204_NO_CONTENT)

        get_response = self.client.get("/api/gestion/ventas-pagos/carrito/")
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data["detalles"], [])
        self.assertEqual(Decimal(get_response.data["total_estimado"]), Decimal("0"))

    def test_usuario_no_cliente_no_puede_gestionar_carrito(self):
        self.client.force_login(self.admin_a)
        response = self.client.get("/api/gestion/ventas-pagos/carrito/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
