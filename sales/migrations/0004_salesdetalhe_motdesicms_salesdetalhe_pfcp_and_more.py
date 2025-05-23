# Generated by Django 5.0.6 on 2025-03-14 13:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0003_salesdetalhe_vicmsdeson'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesdetalhe',
            name='motDesICMS',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='salesdetalhe',
            name='pFCP',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='salesdetalhe',
            name='pFCPST',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='salesdetalhe',
            name='pST',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='salesdetalhe',
            name='vBCSTRet',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='salesdetalhe',
            name='vFCP',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='salesdetalhe',
            name='vFCPST',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='salesdetalhe',
            name='vST',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
    ]
