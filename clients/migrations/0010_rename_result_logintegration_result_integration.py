# Generated by Django 5.0.6 on 2024-06-26 22:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0009_logintegration'),
    ]

    operations = [
        migrations.RenameField(
            model_name='logintegration',
            old_name='result',
            new_name='result_integration',
        ),
    ]