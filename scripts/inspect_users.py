import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')
import django

django.setup()
from django.db import connection

log_file = os.path.join(os.path.dirname(__file__), 'users_inspect.txt')
with connection.cursor() as cursor, open(log_file, 'w', encoding='utf-8') as f:
    cursor.execute('SELECT COUNT(*) FROM usuarios;')
    f.write(f'count={cursor.fetchone()[0]}\n')
    cursor.execute('SELECT id_usuario, correo, is_staff, is_active FROM usuarios ORDER BY id_usuario LIMIT 10;')
    for row in cursor.fetchall():
        f.write(f'{row}\n')

print(f'WROTE {log_file}')
