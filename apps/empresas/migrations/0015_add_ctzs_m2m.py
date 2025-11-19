from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0014_alter_ctzformato_iva_alter_ctzformato_subtotal_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ctzformato',
            name='ctzs',
            field=models.ManyToManyField(blank=True, related_name='formatos_multi', to='empresas.CTZ', verbose_name='CTZs'),
        ),
    ]
