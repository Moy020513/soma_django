from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('asignaciones', '0004_add_completada_if_missing'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE asignaciones_asignacion "
                "ADD COLUMN IF NOT EXISTS fecha_creacion timestamp with time zone NOT NULL DEFAULT NOW();"
            ),
            reverse_sql=("-- no-op"),
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE asignaciones_asignacion "
                "ADD COLUMN IF NOT EXISTS fecha_actualizacion timestamp with time zone NOT NULL DEFAULT NOW();"
            ),
            reverse_sql=("-- no-op"),
        ),
    ]
