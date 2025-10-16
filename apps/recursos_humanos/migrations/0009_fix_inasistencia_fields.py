"""Añade columnas faltantes a la tabla recursos_humanos_inasistencia para alinear
la base de datos con el modelo Inasistencia.

Se usa SQL con `ADD COLUMN IF NOT EXISTS` para ser idempotente en entornos
con estado inconsistente.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recursos_humanos', '0008_inasistencia'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE public.recursos_humanos_inasistencia "
                "ADD COLUMN IF NOT EXISTS tipo varchar(20) DEFAULT 'inasistencia', "
                "ADD COLUMN IF NOT EXISTS dias integer DEFAULT 1, "
                "ADD COLUMN IF NOT EXISTS observaciones text, "
                "ADD COLUMN IF NOT EXISTS registrada_por_id bigint, "
                "ADD COLUMN IF NOT EXISTS fecha_creacion timestamptz DEFAULT now();"
            ),
            reverse_sql=(
                "ALTER TABLE public.recursos_humanos_inasistencia "
                "DROP COLUMN IF EXISTS tipo, "
                "DROP COLUMN IF EXISTS dias, "
                "DROP COLUMN IF EXISTS observaciones, "
                "DROP COLUMN IF EXISTS registrada_por_id, "
                "DROP COLUMN IF EXISTS fecha_creacion;"
            ),
        ),
    ]
