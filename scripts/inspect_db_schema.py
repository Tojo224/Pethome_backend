import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')
import django

django.setup()
from django.db import connection

log_file = os.path.join(os.path.dirname(__file__), 'schema_inspect.txt')
with connection.cursor() as cursor, open(log_file, 'w', encoding='utf-8') as f:
    cursor.execute('SHOW search_path;')
    f.write(f'search_path={cursor.fetchone()[0]}\n')
    cursor.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;")
    rows = cursor.fetchall()
    f.write('schemas=\n')
    for row in rows:
        f.write(f'- {row[0]}\n')

print(f'WROTE {log_file}')
