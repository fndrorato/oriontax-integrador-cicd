# Generated by Django 5.0.6 on 2024-11-04 18:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0006_alter_salesdet_icms_modbc'),
    ]

    operations = [
        migrations.AlterField(
            model_name='salesdet',
            name='CEST',
            field=models.CharField(blank=True, max_length=17, null=True),
        ),
        migrations.AlterField(
            model_name='salesdet',
            name='cEAN',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='salesdet',
            name='cProd',
            field=models.CharField(max_length=50),
        ),
    ]
