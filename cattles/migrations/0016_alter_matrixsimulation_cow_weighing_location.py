# Generated by Django 5.0.6 on 2025-07-12 12:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cattles', '0015_matrixsimulation_is_estorno_icms_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='matrixsimulation',
            name='cow_weighing_location',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
