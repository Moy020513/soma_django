# Generated manually to fix database schema mismatch

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flota_vehicular', '0009_fix_tenenciavehicular_columns_safe'),
    ]

    operations = [
        # Eliminar los campos obsoletos que causan problemas
        migrations.RunSQL(
            "ALTER TABLE flota_vehicular_vehiculo DROP COLUMN IF EXISTS seguro_aseguradora CASCADE;",
            reverse_sql="-- No reverse operation"
        ),
        migrations.RunSQL(
            "ALTER TABLE flota_vehicular_vehiculo DROP COLUMN IF EXISTS seguro_contacto CASCADE;",
            reverse_sql="-- No reverse operation"
        ),
        migrations.RunSQL(
            "ALTER TABLE flota_vehicular_vehiculo DROP COLUMN IF EXISTS seguro_vigencia CASCADE;",
            reverse_sql="-- No reverse operation"
        ),
    ]