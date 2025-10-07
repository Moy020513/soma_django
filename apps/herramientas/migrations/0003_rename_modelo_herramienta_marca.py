from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('herramientas', '0002_refactor_categorias_codigo'),
    ]

    operations = [
        migrations.RenameField(
            model_name='herramienta',
            old_name='modelo',
            new_name='marca',
        ),
    ]
