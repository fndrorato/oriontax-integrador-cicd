# Generated by Django 5.0.6 on 2024-06-07 15:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('impostos', '0016_cbenef_legislation'),
        ('items', '0008_alter_item_cbenef_alter_item_icms_aliquota_reduzida'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='protege',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to='impostos.protege'),
        ),
    ]
