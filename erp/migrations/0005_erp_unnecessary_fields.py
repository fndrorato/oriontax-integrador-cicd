# Generated by Django 5.0.6 on 2024-07-24 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('erp', '0004_remove_erp_unnecessary_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='erp',
            name='unnecessary_fields',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
