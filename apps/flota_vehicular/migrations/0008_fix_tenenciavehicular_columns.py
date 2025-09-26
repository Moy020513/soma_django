from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('flota_vehicular', '0007_add_año_fiscal_to_tenenciavehicular'),
    ]
    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN fecha_vencimiento date;
            ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN fecha_pago date;
            ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN monto numeric(10,2);
            ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN folio varchar(50);
            ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN estado varchar(20);
            ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN comprobante_pago varchar(100);
            ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN observaciones text;
            -- Si ya existen, no se agregan (PostgreSQL ignora si ya existe)
            """,
            reverse_sql="""
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS fecha_vencimiento;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS fecha_pago;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS monto;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS folio;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS estado;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS comprobante_pago;
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN IF EXISTS observaciones;
            """
        ),
    ]
