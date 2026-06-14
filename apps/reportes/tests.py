from django.test import TestCase
from rest_framework.test import APIClient
from django.apps import apps
from django.urls import reverse
from unittest.mock import patch
from datetime import date


class ReportesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Rol = apps.get_model("AutenticacionySeguridad", "Rol")
        User = apps.get_model("AutenticacionySeguridad", "User")
        Veterinaria = apps.get_model("AutenticacionySeguridad", "Veterinaria")
        CategoriaServicio = apps.get_model("GestionServiciosyReserva", "CategoriaServicio")
        Especie = apps.get_model("GestionServiciosyReserva", "Especie")

        cls.rol_super, _ = Rol.objects.get_or_create(nombre=Rol.RolName.SUPERADMIN)
        cls.rol_admin, _ = Rol.objects.get_or_create(nombre=Rol.RolName.ADMIN)
        cls.rol_vet, _ = Rol.objects.get_or_create(nombre=Rol.RolName.VETERINARIAN)

        cls.vet = Veterinaria.objects.create(nombre="Vet Test", slug="vet-test")
        cls.categoria = CategoriaServicio.objects.create(
            nombre="Categoria Test",
            veterinaria=cls.vet,
        )
        cls.especie = Especie.objects.create(nombre="Canino")

        cls.superuser = User.objects.create_user(correo="super@test.com", password="pass", role=cls.rol_super)
        cls.admin = User.objects.create_user(correo="admin@test.com", password="pass", role=cls.rol_admin, veterinaria=cls.vet)
        cls.veterinario = User.objects.create_user(correo="vet@test.com", password="pass", role=cls.rol_vet, veterinaria=cls.vet)

        # create minimal related objects for citas
        Servicio = apps.get_model("GestionServiciosyReserva", "Servicio")
        PrecioServicio = apps.get_model("GestionServiciosyReserva", "PrecioServicio")
        Mascota = apps.get_model("GestionClientesyMascotas", "Mascota")

        cls.servicio = Servicio.objects.create(nombre="Corte", categoria=cls.categoria, veterinaria=cls.vet)
        cls.precio = PrecioServicio.objects.create(servicio=cls.servicio, precio=100, veterinaria=cls.vet)
        cls.mascota = Mascota.objects.create(
            usuario=cls.superuser,
            especie=cls.especie,
            nombre="Doggo",
            veterinaria=cls.vet,
        )

        # create a cita
        Cita = apps.get_model("GestionServiciosyReserva", "Cita")
        cls.cita = Cita.objects.create(usuario=cls.admin, mascota=cls.mascota, servicio=cls.servicio, precio_servicio=cls.precio, fecha_programada=date.today(), hora_inicio="10:00", modalidad=Cita.ModalidadChoices.CLINICA, veterinaria=cls.vet)

    def setUp(self):
        self.client = APIClient()

    def test_permissions_roles(self):
        url = reverse("reportes-kpis")
        # unauthenticated
        r = self.client.get(url)
        self.assertEqual(r.status_code, 401)

        # role not allowed (CLIENT)
        Rol = apps.get_model("AutenticacionySeguridad", "Rol")
        User = apps.get_model("AutenticacionySeguridad", "User")
        rol_client, _ = Rol.objects.get_or_create(nombre=Rol.RolName.CLIENT)
        client_user = User.objects.create_user(correo="ccli@test.com", password="p", role=rol_client)
        self.client.force_authenticate(client_user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

    def test_scope_and_static_generation(self):
        url = reverse("reportes-estaticos-generar")
        self.client.force_authenticate(self.admin)
        payload = {"slug": "citas_por_estado", "filtros": {}, "formato": "pdf"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIn("id", r.data)
        self.assertEqual(r.data["formato"], "PDF")
        self.assertEqual(r.data["veterinaria"], self.vet.id_veterinaria)

        # superadmin generating for specific vet
        self.client.force_authenticate(self.superuser)
        payload = {"slug": "citas_por_estado", "filtros": {"id_veterinaria": self.vet.id_veterinaria}, "formato": "html"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["formato"], "HTML")

    def test_scope_and_static_generation_accepts_alias_payload(self):
        url = reverse("reportes-estaticos-generar")
        self.client.force_authenticate(self.superuser)
        payload = {
            "tipo_reporte": "citas_por_estado",
            "filtros": {
                "fecha_inicio": "2020-01-01",
                "fecha_fin": "2030-01-01",
                "id_veterinaria": self.vet.id_veterinaria,
            },
            "formato": "pdf",
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["tipo_reporte"], "citas_por_estado")
        self.assertEqual(r.data["formato"], "PDF")

    def test_static_report_column_aliases_match_data(self):
        from apps.reportes.services.static_report_service import (
            clientes_registrados,
            mascotas_registradas,
            veterinarios_mas_atenciones,
        )

        scope = {"veterinaria": self.vet}
        for report in (
            clientes_registrados({}, scope),
            mascotas_registradas({}, scope),
            veterinarios_mas_atenciones({}, scope),
        ):
            self.assertTrue(report["columnas"])
            for row in report["datos"]:
                for columna in report["columnas"]:
                    self.assertIn(columna, row)

    def test_export_rejects_error_reports(self):
        from apps.reportes.models import ReporteGenerado

        self.client.force_authenticate(self.admin)
        reporte = ReporteGenerado.objects.create(
            usuario=self.admin,
            veterinaria=self.vet,
            tipo_reporte="fallido",
            origen=ReporteGenerado.OrigenChoices.ESTATICO,
            titulo="Fallido",
            formato=ReporteGenerado.FormatoChoices.PDF,
            estado=ReporteGenerado.EstadoChoices.ERROR,
            columnas=[],
            datos=[],
        )

        export_url = reverse("reportes-exportar", args=[reporte.id_reporte])
        rr = self.client.get(export_url + "?formato=pdf")
        self.assertEqual(rr.status_code, 400)
        self.assertIn("ERROR", str(rr.data).upper())

    def test_dynamic_generation(self):
        url = reverse("reportes-dinamicos-generar")
        self.client.force_authenticate(self.admin)
        payload = {
            "entidad": "citas",
            "metricas": ["cantidad"],
            "dimensiones": ["estado"],
            "filtros": {"fecha_inicio": "2020-01-01", "fecha_fin": "2030-01-01"},
            "formato": "xlsx",
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["formato"], "EXCEL")

    def test_export_endpoints(self):
        # generate a report first
        gen_url = reverse("reportes-estaticos-generar")
        self.client.force_authenticate(self.admin)
        r = self.client.post(gen_url, {"slug": "citas_por_estado", "filtros": {}}, format="json")
        self.assertEqual(r.status_code, 201)
        rep_id = r.data["id_reporte"]

        export_url = reverse("reportes-exportar", args=[rep_id])
        # mock export_service to avoid heavy deps
        with patch("apps.reportes.services.export_service.export_report") as mock_export:
            mock_export.return_value = (b"pdfbytes", "application/pdf", "r.pdf")
            rr = self.client.get(export_url + "?formato=pdf")
            self.assertEqual(rr.status_code, 200)
            self.assertEqual(rr["Content-Type"], "application/pdf")

            mock_export.return_value = (b"xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "r.xlsx")
            rr = self.client.get(export_url + "?formato=xlsx")
            self.assertEqual(rr.status_code, 200)
            self.assertEqual(rr["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            mock_export.return_value = (b"html", "text/html", "r.html")
            rr = self.client.get(export_url + "?formato=html")
            self.assertEqual(rr.status_code, 200)
            self.assertEqual(rr["Content-Type"], "text/html")

    def test_export_excel_real_dynamic_report(self):
        gen_url = reverse("reportes-dinamicos-generar")
        self.client.force_authenticate(self.admin)
        payload = {
            "entidad": "citas",
            "metricas": ["cantidad"],
            "dimensiones": ["estado"],
            "filtros": {"fecha_inicio": "2020-01-01", "fecha_fin": "2030-01-01"},
            "formato": "excel",
        }
        r = self.client.post(gen_url, payload, format="json")
        self.assertEqual(r.status_code, 201)
        rep_id = r.data["id_reporte"]

        export_url = reverse("reportes-exportar", args=[rep_id])
        rr = self.client.get(export_url + "?formato=excel")
        self.assertEqual(rr.status_code, 200)
        self.assertEqual(
            rr["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(rr.content.startswith(b"PK"))

    def test_historial_pagination_and_filters(self):
        # create several reports
        from apps.reportes.models import ReporteGenerado
        for i in range(15):
            ReporteGenerado.objects.create(usuario=self.admin, veterinaria=self.vet, tipo_reporte=f"t{i}", origen=ReporteGenerado.OrigenChoices.ESTATICO, titulo=f"t{i}", formato=ReporteGenerado.FormatoChoices.PDF, estado=ReporteGenerado.EstadoChoices.GENERADO)

        url = reverse("reportes-historial")
        self.client.force_authenticate(self.admin)
        r = self.client.get(url + "?page_size=5")
        self.assertEqual(r.status_code, 200)
        self.assertIn("results", r.data)
        self.assertEqual(len(r.data["results"]), 5)

    def test_dynamic_generation_with_related_dimension_avoids_annotation_conflict(self):
        url = reverse("reportes-dinamicos-generar")
        self.client.force_authenticate(self.admin)

        payload = {
            "entidad": "clientes",
            "metricas": ["cantidad", "activos"],
            "dimensiones": ["veterinaria"],
            "filtros": {},
            "formato": "pdf",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data["datos"])
