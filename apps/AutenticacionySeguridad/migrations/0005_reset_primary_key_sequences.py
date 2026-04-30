# Generated to fix desynchronized PostgreSQL sequences after data restores.

from django.db import migrations


SQL = """
DO $$
DECLARE
    max_user_id bigint;
    max_perfil_id bigint;
BEGIN
    SELECT COALESCE(MAX(id_usuario), 0) INTO max_user_id FROM usuarios;
    IF max_user_id > 0 THEN
        PERFORM setval(pg_get_serial_sequence('usuarios', 'id_usuario'), max_user_id, true);
    ELSE
        PERFORM setval(pg_get_serial_sequence('usuarios', 'id_usuario'), 1, false);
    END IF;

    SELECT COALESCE(MAX(id_perfil), 0) INTO max_perfil_id FROM perfil;
    IF max_perfil_id > 0 THEN
        PERFORM setval(pg_get_serial_sequence('perfil', 'id_perfil'), max_perfil_id, true);
    ELSE
        PERFORM setval(pg_get_serial_sequence('perfil', 'id_perfil'), 1, false);
    END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('AutenticacionySeguridad', '0004_alter_bitacora_modulo_and_more'),
    ]

    operations = [
        migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop),
    ]
