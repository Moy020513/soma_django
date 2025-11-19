from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0014_add_ctzs_m2m'),
        ('empresas', '0014_alter_ctzformato_iva_alter_ctzformato_subtotal_and_more'),
    ]

    operations = [
        # Merge migration: no operations, just a merge point for the two 0014 branches.
    ]
