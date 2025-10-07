from django.db import migrations, models


def forwards(apps, schema_editor):
    # Obtener modelos históricos
    Herramienta = apps.get_model('herramientas', 'Herramienta')
    # Eliminar campos antiguos si existen en la base de datos (Django los manejará vía operaciones)
    # No se requiere lógica de migración de datos para numero_serie -> codigo porque se regenerará al guardar.
    for h in Herramienta.objects.all():
        # Asignar código provisional basado en primeras 3 letras del nombre de la categoría previa (si existiera)
        # Pero la categoría previa se pierde al eliminar el FK, por lo que no podemos mapear aquí.
        # Se deja vacío para que se regenere cuando se edite/guarde.
        pass


def backwards(apps, schema_editor):
    # No se implementa reversa completa porque el modelo CategoriaHerramienta se elimina.
    # Levantamos excepción para dejar claro.
    raise RuntimeError('No se puede revertir esta migración porque elimina CategoriaHerramienta y campos.')


class Migration(migrations.Migration):

    dependencies = [
        ('herramientas', '0001_initial'),
    ]

    operations = [
        # Eliminar FK primero
        migrations.RemoveField(
            model_name='herramienta',
            name='categoria',
        ),
        migrations.RemoveField(
            model_name='herramienta',
            name='numero_serie',
        ),
        migrations.RemoveField(
            model_name='herramienta',
            name='fecha_adquisicion',
        ),
        migrations.RemoveField(
            model_name='herramienta',
            name='costo',
        ),
        # Crear nuevo campo categoria (choices)
        migrations.AddField(
            model_name='herramienta',
            name='categoria',
            field=models.CharField(choices=[('LIM', 'Limpieza'), ('JAR', 'Jardinería'), ('CON', 'Construcción'), ('ELE', 'Electricidad'), ('PIN', 'Pintura'), ('HER', 'Herrería'), ('CAR', 'Carpintería'), ('OTR', 'Otros')], default='OTR', max_length=3),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='herramienta',
            name='codigo',
            field=models.CharField(blank=True, help_text='Se genera automáticamente según la categoría', max_length=20, unique=True),
        ),
        # Eliminar modelo CategoriaHerramienta
        migrations.DeleteModel(
            name='CategoriaHerramienta',
        ),
        migrations.RunPython(forwards, backwards),
    ]
