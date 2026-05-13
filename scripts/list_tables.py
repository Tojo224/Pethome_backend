import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')
import django
django.setup()
from django.db import connection
out = 'scripts/tables_out.txt'
with open(out, 'w', encoding='utf-8') as f:
    f.write(str(sorted(connection.introspection.table_names())))
print('WROTE', out)
