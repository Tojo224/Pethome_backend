from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("AutenticacionySeguridad", "0022_veterinaria_owner_user_billingdemoevent"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                -- dias_retenciÃ³n -> dias_retención
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'backup_config'
                      AND column_name = 'dias_retenciÃ³n'
                ) AND NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'backup_config'
                      AND column_name = 'dias_retención'
                ) THEN
                    ALTER TABLE backup_config RENAME COLUMN "dias_retenciÃ³n" TO "dias_retención";
                END IF;

                -- Ãºltimo_backup -> último_backup
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'backup_config'
                      AND column_name = 'Ãºltimo_backup'
                ) AND NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'backup_config'
                      AND column_name = 'último_backup'
                ) THEN
                    ALTER TABLE backup_config RENAME COLUMN "Ãºltimo_backup" TO "último_backup";
                END IF;

                -- prÃ³ximo_backup_programado -> próximo_backup_programado
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'backup_config'
                      AND column_name = 'prÃ³ximo_backup_programado'
                ) AND NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'backup_config'
                      AND column_name = 'próximo_backup_programado'
                ) THEN
                    ALTER TABLE backup_config RENAME COLUMN "prÃ³ximo_backup_programado" TO "próximo_backup_programado";
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
