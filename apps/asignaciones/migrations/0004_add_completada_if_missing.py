from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('asignaciones', '0003_add_detalles_if_missing'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE asignaciones_asignacion "
                "ADD COLUMN IF NOT EXISTS completada boolean NOT NULL DEFAULT false;"
            ),
            reverse_sql=(
                "-- no-op"
            ),
        ),
    ]
