# Migration to recalculate `fecha` using localtime to respect TIME_ZONE
from django.db import migrations


def recalc_fecha_local(apps, schema_editor):
    Registro = apps.get_model('ubicaciones', 'RegistroUbicacion')
    # Import timezone inside function (migration run environment)
    from django.utils import timezone
    updated = 0
    for r in Registro.objects.all():
        try:
            new_fecha = timezone.localtime(r.timestamp).date()
            if r.fecha != new_fecha:
                r.fecha = new_fecha
                r.save(update_fields=['fecha'])
                updated += 1
        except Exception:
            # skip problematic rows
            continue
    # Optionally print to stdout during migration (not necessary)
    # print(f'Recalculated fecha for {updated} registros')


class Migration(migrations.Migration):

    dependencies = [
        ('ubicaciones', '0003_add_fecha_and_unique'),
    ]

    operations = [
        # Antes de recalcular `fecha`, eliminar duplicados potenciales según la fecha local
        migrations.RunSQL(
            sql="""
            DELETE FROM ubicaciones_registroubicacion
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY empleado_id, tipo, ((timestamp AT TIME ZONE 'America/Mexico_City')::date)
                        ORDER BY timestamp ASC
                    ) AS rn
                    FROM ubicaciones_registroubicacion
                ) t
                WHERE t.rn > 1
            );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunPython(recalc_fecha_local, reverse_code=migrations.RunPython.noop),
    ]
