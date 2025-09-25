from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('asignaciones', '0002_alter_asignacion_unique_together'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE asignaciones_asignacion "
                "ADD COLUMN IF NOT EXISTS detalles text NOT NULL DEFAULT '';"
            ),
            reverse_sql=(
                # No eliminamos la columna en reversa por seguridad
                "-- no-op"
            ),
        ),
    ]
