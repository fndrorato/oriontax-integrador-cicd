# Generated by Django 5.0.6 on 2025-03-19 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0004_salesdetalhe_motdesicms_salesdetalhe_pfcp_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesdetalhe',
            name='chNFe',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
