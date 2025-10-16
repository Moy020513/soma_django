"""Migra datos legacy y añade constraint FK para registrada_por_id.

Operaciones:
- Copiar `motivo` -> `observaciones` si observaciones es NULL.
- Copiar `fecha_registro` -> `fecha_creacion` si fecha_creacion es NULL.
- Añadir constraint FK para `registrada_por_id` hacia `usuarios_usuario(id)` con ON DELETE SET NULL,
  si no existe previamente.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recursos_humanos', '0009_fix_inasistencia_fields'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                # crear FK si no existe
                "DO $$\nBEGIN\n    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'recursos_inasistencia_registrada_por_fk') THEN\n        ALTER TABLE public.recursos_humanos_inasistencia\n        ADD CONSTRAINT recursos_inasistencia_registrada_por_fk FOREIGN KEY (registrada_por_id) REFERENCES public.usuarios_usuario(id) ON DELETE SET NULL;\n    END IF;\nEND$$;"
            ),
            reverse_sql=(
                "DO $$\nBEGIN\n    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'recursos_inasistencia_registrada_por_fk') THEN\n        ALTER TABLE public.recursos_humanos_inasistencia DROP CONSTRAINT recursos_inasistencia_registrada_por_fk;\n    END IF;\nEND$$;"
            ),
        ),
    ]
