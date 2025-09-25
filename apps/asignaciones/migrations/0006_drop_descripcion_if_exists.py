from django.db import migrations


SQL = r'''
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'asignaciones_asignacion'
      AND column_name = 'descripcion'
  ) THEN
    -- Copiar datos a detalles si corresponde
    IF EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'asignaciones_asignacion'
        AND column_name = 'detalles'
    ) THEN
      UPDATE asignaciones_asignacion
      SET detalles = COALESCE(detalles, descripcion)
      WHERE descripcion IS NOT NULL;
    END IF;
    -- Quitar NOT NULL y eliminar la columna
    ALTER TABLE asignaciones_asignacion ALTER COLUMN descripcion DROP NOT NULL;
    ALTER TABLE asignaciones_asignacion DROP COLUMN descripcion;
  END IF;
END $$;
'''


class Migration(migrations.Migration):

    dependencies = [
        ('asignaciones', '0005_add_timestamps_if_missing'),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql='-- no-op'),
    ]
