from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.AutenticacionySeguridad.services import BackupScheduler
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ejecuta el scheduler de backups automáticos. Diseñado para ejecutarse como cron job cada 30 minutos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Muestra detalles adicionales de ejecución',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la ejecución sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        dry_run = options['dry_run']
        
        try:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('[DRY RUN] Ejecutando scheduler en modo simulación...')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('Iniciando scheduler de backups automáticos...')
                )
                self.stdout.write(f'Hora actual: {timezone.now()}')
            
            # Ejecutar scheduler
            summary = BackupScheduler.run_scheduled_backups()
            
            # Mostrar resumen
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Backups procesados: {summary["total_processed"]}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Exitosos: {summary["successful"]}')
            )
            if summary["failed"] > 0:
                self.stdout.write(
                    self.style.ERROR(f'✗ Fallidos: {summary["failed"]}')
                )
            if summary.get("skipped", 0) > 0:
                self.stdout.write(
                    self.style.WARNING(f'⊘ Saltados (no es hora): {summary["skipped"]}')
                )
            
            if summary["errors"]:
                self.stdout.write(self.style.WARNING('\nErrores encontrados:'))
                for error in summary["errors"]:
                    self.stdout.write(f'  - {error}')
            
            if verbose:
                self.stdout.write(self.style.SUCCESS(f'\nResumen completo: {summary}'))
            
            if summary["failed"] > 0 and not dry_run:
                raise CommandError(
                    f'Scheduler completado con {summary["failed"]} fallos. Ver detalles arriba.'
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('\n✓ Scheduler completado exitosamente')
                )
        
        except Exception as e:
            logger.exception(f"Error ejecutando backup scheduler: {str(e)}")
            raise CommandError(f'Error ejecutando scheduler: {str(e)}')
