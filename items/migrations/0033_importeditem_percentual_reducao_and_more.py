# Generated by Django 5.0.6 on 2025-06-17 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0032_alter_importeditem_icms_aliquota_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='importeditem',
            name='percentual_reducao',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='item',
            name='percentual_reducao',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=5, null=True),
        ),
    ]
