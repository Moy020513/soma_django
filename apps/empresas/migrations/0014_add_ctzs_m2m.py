from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0013_preserve_total_and_add_iva'),
    ]

    operations = [
        migrations.AddField(
            model_name='ctzformato',
            name='ctzs',
            field=models.ManyToManyField(blank=True, related_name='formatos_multi', to='empresas.CTZ', verbose_name='CTZs'),
        ),
    ]
