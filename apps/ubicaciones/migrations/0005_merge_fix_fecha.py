from django.db import migrations


class Migration(migrations.Migration):

    # Esta migración mergea las dos ramas 0004 que se generaron en ubicaciones
    dependencies = [
        ('ubicaciones', '0004_fix_fecha_localtime'),
        ('ubicaciones', '0004_registroubicacion_ubicaciones_fecha_a625c6_idx'),
    ]

    operations = [
        # No-op: solo un merge para resolver el grafo de migraciones
    ]
