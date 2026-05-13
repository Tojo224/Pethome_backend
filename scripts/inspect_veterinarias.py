import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')
import django

django.setup()
from django.db import connection

log_file = os.path.join(os.path.dirname(__file__), 'veterinarias_inspect.txt')
with connection.cursor() as cursor, open(log_file, 'w', encoding='utf-8') as f:
    cursor.execute('SELECT COUNT(*) FROM veterinaria;')
    f.write(f'count={cursor.fetchone()[0]}\n')
    cursor.execute('SELECT id_veterinaria, nombre, slug, estado FROM veterinaria ORDER BY id_veterinaria;')
    for row in cursor.fetchall():
        f.write(f'{row}\n')

print(f'WROTE {log_file}')
