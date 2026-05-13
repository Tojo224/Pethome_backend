import os
import sys
import subprocess

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pethome_back.settings')
import django
django.setup()
from django.conf import settings
from decouple import config
from google.cloud import storage

def main():
    blob_path = 'backups/veterinaria_2/backup_2_20260509_234102.sql'
    local_file = 'restore_backup_20260509.sql'
    client = storage.Client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(blob_path)
    if not blob.exists():
        print('ERROR: blob not found')
        sys.exit(2)
    blob.download_to_filename(local_file)

    psql_path = getattr(settings, 'PSQL_PATH', 'psql') or 'psql'
    try:
        db_url = config('DATABASE_URL')
    except Exception:
        db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print('ERROR: DATABASE_URL not found')
        sys.exit(3)

    # parse URL
    from urllib.parse import urlparse, unquote
    u = urlparse(db_url)
    host = u.hostname or ''
    port = str(u.port or '')
    user = unquote(u.username) if u.username else ''
    password = unquote(u.password) if u.password else ''
    dbname = u.path[1:]

    cmd = [psql_path]
    if host:
        cmd += ['-h', host]
    if port:
        cmd += ['-p', port]
    if user:
        cmd += ['-U', user]
    if dbname:
        cmd += ['-d', dbname]

    env = os.environ.copy()
    if password:
        env['PGPASSWORD'] = password

    log_file = os.path.join(os.path.dirname(__file__), 'restore_v2_log.txt')
    debug_file = os.path.join(os.path.dirname(__file__), 'restore_v2_debug.txt')
    with open(debug_file, 'w', encoding='utf-8') as df:
        df.write(f'cmd={cmd}\n')
        df.write(f'host={host} port={port} user={user} db={dbname}\n')

    with open(local_file, 'rb') as sqlf, open(log_file, 'wb') as lf:
        proc = subprocess.run(cmd, stdin=sqlf, stdout=lf, stderr=subprocess.STDOUT, env=env)

    with open(debug_file, 'a', encoding='utf-8') as df:
        df.write(f'returncode={proc.returncode}\n')

    print('Wrote', log_file, debug_file)
    if proc.returncode != 0:
        sys.exit(proc.returncode)

if __name__ == '__main__':
    main()
