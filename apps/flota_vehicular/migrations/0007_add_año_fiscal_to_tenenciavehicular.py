from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('flota_vehicular', '0006_vehiculo_numero_seguro'),
    ]
    operations = [
        migrations.RunSQL(
            sql="""
            DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='flota_vehicular_tenenciavehicular' AND column_name='año_fiscal'
            ) THEN
                ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN año_fiscal integer;
            END IF;
            END $$;
            """,
            reverse_sql="""
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS año_fiscal;
            """
        ),
    ]
