from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('herramientas', '0005_transferenciaherramienta'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferenciaherramienta',
            name='fecha_inspeccion',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transferenciaherramienta',
            name='observaciones_inspeccion',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='transferenciaherramienta',
            name='estado',
            field=models.CharField(choices=[('solicitada', 'Solicitada'), ('inspeccion', 'En Inspección'), ('aprobada', 'Aprobada'), ('rechazada', 'Rechazada'), ('cancelada', 'Cancelada')], default='solicitada', max_length=20),
        ),
    ]
