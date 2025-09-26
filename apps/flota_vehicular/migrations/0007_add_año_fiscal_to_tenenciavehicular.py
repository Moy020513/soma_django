from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('flota_vehicular', '0006_vehiculo_numero_seguro'),
    ]
    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE flota_vehicular_tenenciavehicular ADD COLUMN año_fiscal integer;
            """,
            reverse_sql="""
            ALTER TABLE flota_vehicular_tenenciavehicular DROP COLUMN año_fiscal;
            """
        ),
    ]
