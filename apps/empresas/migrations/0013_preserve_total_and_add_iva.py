"""Preserve existing `total` values by renaming to `subtotal`, then add `iva` and new `total`.

Steps:
 - Rename old column `total` -> `subtotal` (preserves values)
 - Add `iva` and new `total` columns (nullable)
 - Populate `iva` = 16% of subtotal and `total` = subtotal + iva
 - Make `iva` and `total` non-null with default=0
"""
from django.db import migrations, models


def forwards(apps, schema_editor):
    CTZFormato = apps.get_model('empresas', 'CTZFormato')
    for obj in CTZFormato.objects.all():
        try:
            subtotal = float(obj.subtotal or 0)
        except Exception:
            subtotal = 0.0
        iva = round(subtotal * 0.16, 2)
        total = round(subtotal + iva, 2)
        obj.iva = iva
        obj.total = total
        obj.save(update_fields=['iva', 'total'])


def backwards(apps, schema_editor):
    CTZFormato = apps.get_model('empresas', 'CTZFormato')
    for obj in CTZFormato.objects.all():
        try:
            # revert: set total back to subtotal (best-effort)
            obj.total = float(obj.subtotal or 0)
            obj.iva = 0
            obj.save(update_fields=['iva', 'total'])
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0012_ctzformato'),
    ]

    operations = [
        # rename old `total` column to `subtotal` to preserve existing values
        migrations.RenameField(
            model_name='ctzformato',
            old_name='total',
            new_name='subtotal',
        ),
        # add iva and total (new) as nullable fields first
        migrations.AddField(
            model_name='ctzformato',
            name='iva',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name='ctzformato',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, null=True),
        ),
        # populate iva and total based on subtotal
        migrations.RunPython(forwards, backwards),
        # make iva and total non-nullable with default 0
        migrations.AlterField(
            model_name='ctzformato',
            name='iva',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name='ctzformato',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
    ]
