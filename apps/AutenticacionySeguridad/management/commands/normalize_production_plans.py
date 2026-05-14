from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.AutenticacionySeguridad.models.plan_suscripcion import PlanSuscripcion
from apps.AutenticacionySeguridad.models.suscripcion import Suscripcion
from apps.AutenticacionySeguridad.models.veterinaria import Veterinaria


class Command(BaseCommand):
    help = "Normaliza planes a Starter/Pro/Enterprise y asigna Enterprise a veterinarias existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        starter, _ = PlanSuscripcion.objects.update_or_create(
            nombre="Starter",
            defaults={
                "descripcion": "Plan inicial con acceso movil, sin reportes ni backups.",
                "precio_mensual": 0,
                "limite_usuarios": 5,
                "limite_mascotas": 300,
                "permite_app_movil": True,
                "permite_reportes": False,
                "permite_backup": False,
                "estado": True,
            },
        )

        pro, _ = PlanSuscripcion.objects.update_or_create(
            nombre="Pro",
            defaults={
                "descripcion": "Plan profesional con reportes y backups.",
                "precio_mensual": 0,
                "limite_usuarios": 20,
                "limite_mascotas": 2000,
                "permite_app_movil": True,
                "permite_reportes": True,
                "permite_backup": True,
                "estado": True,
            },
        )

        enterprise, _ = PlanSuscripcion.objects.update_or_create(
            nombre="Enterprise",
            defaults={
                "descripcion": "Plan empresarial con todas las capacidades habilitadas.",
                "precio_mensual": 0,
                "limite_usuarios": 1000,
                "limite_mascotas": 50000,
                "permite_app_movil": True,
                "permite_reportes": True,
                "permite_backup": True,
                "estado": True,
            },
        )

        today = date.today()
        moved = 0
        for vet in Veterinaria.objects.all():
            Suscripcion.objects.filter(
                veterinaria=vet,
                estado_suscripcion__in=["ACTIVA", "PRUEBA"],
            ).update(
                estado_suscripcion="CANCELADA",
                fecha_fin=today,
                renovacion_automatica=False,
            )

            Suscripcion.objects.create(
                veterinaria=vet,
                plan=enterprise,
                fecha_inicio=today,
                fecha_fin=None,
                estado_suscripcion="ACTIVA",
                renovacion_automatica=True,
            )
            moved += 1

        self.stdout.write(self.style.SUCCESS(f"Planes normalizados: Starter({starter.id_plan}), Pro({pro.id_plan}), Enterprise({enterprise.id_plan})"))
        self.stdout.write(self.style.SUCCESS(f"Veterinarias migradas a Enterprise: {moved}"))
