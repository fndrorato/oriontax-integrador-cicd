# Generated by Django 5.0.6 on 2024-05-29 19:49

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Cfop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cfop', models.PositiveIntegerField(unique=True)),
            ],
            options={
                'verbose_name': 'CFOP',
                'verbose_name_plural': 'CFOPs',
            },
        ),
    ]
