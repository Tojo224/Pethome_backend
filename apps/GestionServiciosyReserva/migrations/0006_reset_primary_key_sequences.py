# Generated to fix desynchronized PostgreSQL sequences after data restores.

from django.db import migrations


SQL = """
DO $$
DECLARE
    max_categoria_id bigint;
    max_servicio_id bigint;
    max_precio_id bigint;
    max_cita_id bigint;
BEGIN
    SELECT COALESCE(MAX(id_categoria), 0) INTO max_categoria_id FROM categorias_servicio;
    IF max_categoria_id > 0 THEN
        PERFORM setval(pg_get_serial_sequence('categorias_servicio', 'id_categoria'), max_categoria_id, true);
    ELSE
        PERFORM setval(pg_get_serial_sequence('categorias_servicio', 'id_categoria'), 1, false);
    END IF;

    SELECT COALESCE(MAX(id_servicio), 0) INTO max_servicio_id FROM servicios;
    IF max_servicio_id > 0 THEN
        PERFORM setval(pg_get_serial_sequence('servicios', 'id_servicio'), max_servicio_id, true);
    ELSE
        PERFORM setval(pg_get_serial_sequence('servicios', 'id_servicio'), 1, false);
    END IF;

    SELECT COALESCE(MAX(id_precio), 0) INTO max_precio_id FROM precios_servicio;
    IF max_precio_id > 0 THEN
        PERFORM setval(pg_get_serial_sequence('precios_servicio', 'id_precio'), max_precio_id, true);
    ELSE
        PERFORM setval(pg_get_serial_sequence('precios_servicio', 'id_precio'), 1, false);
    END IF;

    SELECT COALESCE(MAX(id_cita), 0) INTO max_cita_id FROM cita;
    IF max_cita_id > 0 THEN
        PERFORM setval(pg_get_serial_sequence('cita', 'id_cita'), max_cita_id, true);
    ELSE
        PERFORM setval(pg_get_serial_sequence('cita', 'id_cita'), 1, false);
    END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("GestionServiciosyReserva", "0005_enforce_not_null_veterinaria"),
    ]

    operations = [
        migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop),
    ]