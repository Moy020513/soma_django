from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recursos_humanos', '0001_initial'),
        ('herramientas', '0004_remove_herramienta_descripcion'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransferenciaHerramienta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_solicitud', models.DateTimeField(auto_now_add=True)),
                ('fecha_respuesta', models.DateTimeField(blank=True, null=True)),
                ('fecha_transferencia', models.DateTimeField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('solicitada', 'Solicitada'), ('aprobada', 'Aprobada'), ('rechazada', 'Rechazada'), ('cancelada', 'Cancelada')], default='solicitada', max_length=20)),
                ('observaciones_solicitud', models.TextField(blank=True)),
                ('observaciones_respuesta', models.TextField(blank=True)),
                ('empleado_destino', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transferencias_herramientas_destino', to='recursos_humanos.empleado')),
                ('empleado_origen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transferencias_herramientas_origen', to='recursos_humanos.empleado')),
                ('herramienta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='herramientas.herramienta')),
            ],
            options={
                'verbose_name': 'Transferencia de Herramienta',
                'verbose_name_plural': 'Transferencias de Herramientas',
                'ordering': ['-fecha_solicitud'],
            },
        ),
    ]
