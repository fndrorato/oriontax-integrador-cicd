# Generated by Django 5.0.6 on 2024-06-06 23:17

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0006_alter_client_day_sent'),
        ('impostos', '0016_cbenef_legislation'),
        ('items', '0006_fix_constraints'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='item',
            name='unique_store_code',
        ),
        migrations.RemoveField(
            model_name='item',
            name='store',
        ),
        migrations.AddConstraint(
            model_name='item',
            constraint=models.UniqueConstraint(fields=('client', 'code'), name='unique_client_code'),
        ),
    ]
