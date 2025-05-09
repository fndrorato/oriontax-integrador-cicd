# Generated by Django 5.0.6 on 2024-05-29 19:58

import impostos.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('impostos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cfop',
            name='description',
            field=models.CharField(blank=True, default='Descrição CFOP', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='cfop',
            name='operation',
            field=models.CharField(default='S', max_length=1, validators=[impostos.models.validate_operation]),
        ),
        migrations.AlterField(
            model_name='cfop',
            name='cfop',
            field=models.PositiveIntegerField(unique=True, validators=[impostos.models.validate_cfop]),
        ),
    ]
