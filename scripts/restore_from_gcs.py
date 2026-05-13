import os
import sys
import subprocess

# Ensure project root is on sys.path when running script directly
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
    print('Bucket:', settings.GCS_BUCKET_NAME)
    print('Downloading', blob_path, 'to', local_file)
    client = storage.Client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(blob_path)
    if not blob.exists():
        print('ERROR: blob not found')
        sys.exit(2)
    blob.download_to_filename(local_file)
    print('Downloaded OK, size=', os.path.getsize(local_file))

    psql_path = getattr(settings, 'PSQL_PATH', 'psql') or 'psql'
    print('Using psql:', psql_path)
    try:
        db_url = config('DATABASE_URL')
    except Exception:
        db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print('ERROR: DATABASE_URL not found in env or .env')
        sys.exit(3)

    print('Restoring to database...')
    # Parse DATABASE_URL and call psql with explicit host/port/db/user and PGPASSWORD
    try:
        import dj_database_url
        parsed = dj_database_url.parse(db_url)
    except Exception:
        # fallback: naive parse
        from urllib.parse import urlparse, unquote
        u = urlparse(db_url)
        parsed = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': u.path[1:],
            'USER': unquote(u.username) if u.username else '',
            'PASSWORD': unquote(u.password) if u.password else '',
            'HOST': u.hostname or '',
            'PORT': u.port or '',
        }

    host = parsed.get('HOST') or parsed.get('HOSTNAME') or ''
    port = str(parsed.get('PORT') or '')
    user = parsed.get('USER') or parsed.get('USER')
    password = parsed.get('PASSWORD') or ''
    dbname = parsed.get('NAME') or parsed.get('DB_NAME') or ''

    cmd = [psql_path]
    if host:
        cmd += ['-h', host]
    if port:
        cmd += ['-p', port]
    if user:
        cmd += ['-U', user]
    if dbname:
        cmd += ['-d', dbname]
    cmd += ['-f', local_file]

    print('Running:', ' '.join(cmd))
    env = os.environ.copy()
    debug_file = os.path.join(os.path.dirname(__file__), 'restore_debug.txt')
    with open(debug_file, 'w', encoding='utf-8') as df:
        df.write(f'psql_path={psql_path}\n')
        df.write(f'psql_exists={os.path.exists(psql_path)}\n')
        df.write(f'host={host} port={port} user={user} dbname={dbname}\n')
        df.write(f'cmd={cmd}\n')
        df.write(f'DB_URL_sample={db_url[:80]}...\n')
    if password:
        env['PGPASSWORD'] = password
    log_file = os.path.join(os.path.dirname(__file__), 'restore_log.txt')
    with open(log_file, 'wb') as lf:
        proc = subprocess.run(cmd, shell=False, stdout=lf, stderr=subprocess.STDOUT, env=env)
    with open(debug_file, 'a', encoding='utf-8') as df:
        df.write(f'psql_returncode={proc.returncode}\n')
    print('psql exit code=', proc.returncode)
    print('Wrote log to', log_file)
    if proc.returncode != 0:
        sys.exit(proc.returncode)
    print('Restore completed')

if __name__ == '__main__':
    main()
