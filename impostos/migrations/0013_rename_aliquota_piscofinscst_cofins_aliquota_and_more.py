# Generated by Django 5.0.6 on 2024-06-04 00:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('impostos', '0012_remove_cfop_id_alter_cfop_cfop'),
    ]

    operations = [
        migrations.RenameField(
            model_name='piscofinscst',
            old_name='aliquota',
            new_name='cofins_aliquota',
        ),
        migrations.AddField(
            model_name='cbenef',
            name='description',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='naturezareceita',
            name='category',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='piscofinscst',
            name='description',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='piscofinscst',
            name='pis_aliquota',
            field=models.FloatField(default=0),
        ),
    ]
