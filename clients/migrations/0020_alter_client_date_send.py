# Generated by Django 5.0.6 on 2024-10-11 19:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0019_alter_client_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='date_send',
            field=models.DateField(blank=True, null=True),
        ),
    ]
