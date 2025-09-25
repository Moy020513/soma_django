from django.db import migrations


SQL = r'''
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'asignaciones_asignacion'
      AND column_name = 'tiempo_estimado_horas'
  ) THEN
    ALTER TABLE asignaciones_asignacion DROP COLUMN tiempo_estimado_horas;
  END IF;
END $$;
'''


class Migration(migrations.Migration):

    dependencies = [
        ('asignaciones', '0006_drop_descripcion_if_exists'),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql='-- no-op'),
    ]
