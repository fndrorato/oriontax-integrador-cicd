# Generated by Django 5.0.6 on 2024-07-19 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0024_item_await_sync_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='await_sync_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='sync_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]