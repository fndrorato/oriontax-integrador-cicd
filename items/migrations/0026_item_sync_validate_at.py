# Generated by Django 5.0.6 on 2024-07-19 16:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0025_alter_item_await_sync_at_alter_item_sync_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='sync_validate_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]