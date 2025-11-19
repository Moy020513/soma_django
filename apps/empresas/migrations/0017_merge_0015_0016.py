from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0015_add_ctzs_m2m'),
        ('empresas', '0016_merge_0014s'),
    ]

    operations = [
        # Merge node to resolve multiple leaf nodes
    ]
