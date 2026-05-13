import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')

from django.core.management import call_command
import django

django.setup()

log_file = os.path.join(os.path.dirname(__file__), 'migrate_log.txt')
with open(log_file, 'w', encoding='utf-8') as f:
    try:
        call_command('migrate', '--noinput', verbosity=2, stdout=f, stderr=f)
    except Exception as exc:
        f.write(f'EXCEPTION: {exc!r}\n')
        raise

print(f'WROTE {log_file}')
