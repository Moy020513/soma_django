from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('herramientas', '0003_rename_modelo_herramienta_marca'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='herramienta',
            name='descripcion',
        ),
    ]
