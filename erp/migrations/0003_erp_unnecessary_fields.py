# Generated by Django 5.0.6 on 2024-07-24 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('erp', '0002_rename_erpmodel_erp'),
    ]

    operations = [
        migrations.AddField(
            model_name='erp',
            name='unnecessary_fields',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
    ]