from django.db import migrations


SQL = r'''
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'asignaciones_asignacion'
      AND column_name = 'creado_en'
  ) THEN
    ALTER TABLE asignaciones_asignacion DROP COLUMN creado_en;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'asignaciones_asignacion'
      AND column_name = 'actualizado_en'
  ) THEN
    ALTER TABLE asignaciones_asignacion DROP COLUMN actualizado_en;
  END IF;
END $$;
'''


class Migration(migrations.Migration):

    dependencies = [
        ('asignaciones', '0007_drop_tiempo_estimado_if_exists'),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql='-- no-op'),
    ]
