from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('flota_vehicular', '0008_fix_tenenciavehicular_columns'),
    ]
    operations = [
        migrations.RunSQL(
            sql="""
            DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='flota_vehicular_tenenciavehicular' AND column_name='fecha_vencimiento') THEN
                ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN fecha_vencimiento date;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='flota_vehicular_tenenciavehicular' AND column_name='monto') THEN
                ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN monto numeric(10,2);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='flota_vehicular_tenenciavehicular' AND column_name='folio') THEN
                ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN folio varchar(50);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='flota_vehicular_tenenciavehicular' AND column_name='estado') THEN
                ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN estado varchar(20);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='flota_vehicular_tenenciavehicular' AND column_name='comprobante_pago') THEN
                ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN comprobante_pago varchar(100);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='flota_vehicular_tenenciavehicular' AND column_name='observaciones') THEN
                ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN observaciones text;
            END IF;
            END $$;
            """,
            reverse_sql="""
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS fecha_vencimiento;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS monto;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS folio;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS estado;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS comprobante_pago;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS observaciones;
            """
        ),
    ]
