# Generated by Django 5.0.6 on 2025-03-29 20:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0005_salesdetalhe_chnfe'),
    ]

    operations = [
        migrations.RenameField(
            model_name='salespedido',
            old_name='tpAmb',
            new_name='tpamb',
        ),
    ]
