# Generated by Django 5.0.6 on 2024-07-19 12:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0020_alter_importeditem_code_alter_item_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='sync_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
